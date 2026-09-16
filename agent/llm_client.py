"""Provider boundary; no engineering calculations. / 模型服务适配层，不执行工程计算。"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from .tool_definitions import FINAL_SCHEMA

ROOT = Path(__file__).resolve().parents[1]


class ConfigurationError(ValueError):
    pass


class ProviderError(RuntimeError):
    """Safe errors contain no remote response body. / 安全错误不含远程响应正文。"""


@dataclass(frozen=True)
class Settings:
    api_key: str = field(repr=False)
    model: str
    timeout: float = 45.0
    max_rounds: int = 6
    provider: str = "openai"
    allow_paid_models: bool = False

    @classmethod
    def load(cls, root=ROOT, environ=None):
        from dotenv import dotenv_values

        # Environment takes precedence; no interpolation or mutation of os.environ.
        # 环境变量优先，不展开变量，也不修改进程环境。
        values = dict(
            dotenv_values(Path(root) / ".env", encoding="utf-8-sig", interpolate=False)
        )
        values.update(os.environ if environ is None else environ)
        provider = values.get("LLM_PROVIDER", "openai").strip().lower()
        if provider not in {"openai", "openrouter"}:
            raise ConfigurationError("Unsupported provider / 不支持的模型服务")
        fallback = (
            "OPENROUTER_API_KEY" if provider == "openrouter" else "OPENAI_API_KEY"
        )
        key = (values.get("LLM_API_KEY") or values.get(fallback) or "").strip()
        model = (
            values.get("LLM_MODEL")
            or ("openrouter/free" if provider == "openrouter" else "")
        ).strip()
        if not key or key in {"YOUR_API_KEY", "..."}:
            raise ConfigurationError(
                "Set LLM_API_KEY in local .env / 请在本地 .env 设置 LLM_API_KEY"
            )
        if (
            not model
            or model in {"YOUR_MODEL_ID", "..."}
            or not re.fullmatch(r"[\w./:-]{1,100}", model)
        ):
            raise ConfigurationError(
                "Set a valid LLM_MODEL in local .env / 请在本地 .env 设置有效的 LLM_MODEL"
            )
        paid = (values.get("LLM_ALLOW_PAID_MODELS") or "false").strip().lower()
        if paid not in {"true", "false"}:
            raise ConfigurationError(
                "LLM_ALLOW_PAID_MODELS must be true or false / 付费开关须为 true 或 false"
            )
        if (
            provider == "openrouter"
            and paid == "false"
            and model != "openrouter/free"
            and not model.endswith(":free")
        ):
            raise ConfigurationError(
                "Free models only: use openrouter/free or a :free model / 默认仅允许免费模型"
            )
        try:
            timeout = float(values.get("LLM_TIMEOUT_SECONDS") or 45)
            rounds = int(values.get("LLM_MAX_TOOL_ROUNDS") or 6)
            if not 1 <= timeout <= 120 or not 1 <= rounds <= 12:
                raise ValueError
        except (ValueError, TypeError):
            raise ConfigurationError(
                "Invalid timeout or round limit / 超时或调用轮数配置无效"
            ) from None
        return cls(key, model, timeout, rounds, provider, paid == "true")


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    name: str
    arguments: str


@dataclass
class ModelReply:
    calls: list[ToolCall] = field(default_factory=list)
    text: str = ""
    history_items: list[dict] = field(default_factory=list)


class ModelClient(Protocol):
    def complete(
        self, history: list[dict], instructions: str, tools: list[dict]
    ) -> ModelReply: ...


class OpenAIClient:
    def __init__(self, settings: Settings, sdk_client=None):
        from openai import OpenAI

        self.settings = settings
        # SDK debug logs may contain conversation data. / 避免 SDK 调试日志记录会话内容。
        for name in ("openai", "httpx", "httpx2", "httpcore", "httpcore2"):
            logging.getLogger(name).disabled = True
        self._client = sdk_client or OpenAI(
            api_key=settings.api_key,
            timeout=settings.timeout,
            max_retries=1,
            base_url=(
                "https://openrouter.ai/api/v1"
                if settings.provider == "openrouter"
                else "https://api.openai.com/v1"
            ),
        )

    def complete(self, history, instructions, tools):
        from openai import APIConnectionError, APIStatusError, APITimeoutError

        options = {
            "include": ["reasoning.encrypted_content"],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "capacity_answer",
                    "strict": True,
                    "schema": FINAL_SCHEMA,
                }
            },
        }
        if self.settings.provider == "openrouter":
            # Some free endpoints omit optional parameter support from their metadata.
            # 免费服务的元数据可能未声明可选参数支持；工具参数仍由本地严格校验。
            routing = {}
            if not self.settings.allow_paid_models:
                routing["max_price"] = {"prompt": 0, "completion": 0}
            options = {"extra_body": {"provider": routing}}
            options["reasoning"] = {"effort": "low"}
            instructions += (
                "\nReturn the final answer as a JSON object, without markdown fences, "
                "matching this schema (tool calls must use the API tools): "
                + json.dumps(FINAL_SCHEMA)
            )
        try:
            response = self._client.responses.create(
                model=self.settings.model,
                instructions=instructions,
                input=history,
                tools=tools,
                parallel_tool_calls=False,
                store=False,
                **options,
                max_output_tokens=8192
                if self.settings.provider == "openrouter"
                else 4096,
            )
        except APITimeoutError:
            raise ProviderError(
                "Model request timed out; try again / 模型请求超时，请重试"
            ) from None
        except APIConnectionError:
            raise ProviderError(
                "Cannot connect to model service / 无法连接模型服务，请检查网络"
            ) from None
        except APIStatusError as exc:
            if exc.status_code in (401, 403):
                message = (
                    "Check API key and model access / 请检查 API Key 及模型访问权限"
                )
            elif exc.status_code == 402:
                message = "Provider credit limit reached; check account and model / 服务额度受限，请检查账户与所选模型"
            elif exc.status_code == 404:
                message = "No compatible model endpoint available (HTTP 404) / 无可用的兼容模型服务，请检查模型及路由限制（HTTP 404）"
            elif exc.status_code == 429:
                message = "API rate or quota limit reached / API 请求频率或额度受限"
            else:
                message = "Model service rejected the request; check model support / 模型服务拒绝请求，请检查模型兼容性"
            raise ProviderError(message) from None
        if response.status != "completed":
            raise ProviderError(
                "Model response was incomplete / 模型响应未完成，请重试"
            )
        calls = []
        items = []
        for item in response.output:
            items.append(item.model_dump(mode="json", exclude_none=True))
            if item.type == "function_call":
                calls.append(ToolCall(item.call_id, item.name, item.arguments))
            elif item.type == "message" and any(
                part.type == "refusal" for part in item.content
            ):
                raise ProviderError(
                    "The model declined this request / 模型拒绝了本次请求"
                )
        return ModelReply(calls, response.output_text or "", items)

    def close(self):
        self._client.close()


def strict_json(text):
    def invalid_constant(_):
        raise ValueError("Nonfinite JSON")

    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON field")
            result[key] = value
        return result

    if not isinstance(text, str) or len(text) > 100000:
        raise ValueError("Invalid JSON length")
    return json.loads(
        text, parse_constant=invalid_constant, object_pairs_hook=unique_pairs
    )
