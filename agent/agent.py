"""Bounded tool loop with session-local computed results. / 有界工具循环与会话计算结果。"""

import json
import re
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from jsonschema import Draft202012Validator

from .knowledge import search_knowledge
from .llm_client import ModelClient, ProviderError, strict_json
from .prompts import system_prompt
from .schemas import ToolValidationError
from .tool_definitions import FINAL_SCHEMA, tool_definitions
from .tools import ROOT, dispatch_tool, generate_capacity_plot


@dataclass
class TurnResult:
    english: str
    chinese: str
    records: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    status: str = "answer"


def _error(code, message):
    return {"ok": False, "error": {"code": code, "message": message}}


def _compact(data):
    result = deepcopy(data)
    if len(result.get("rows", [])) > 12:
        rows = result["rows"]
        result["rows"] = rows[:6] + rows[-6:]
        result["rows_truncated"] = True
        result["full_row_count"] = len(rows)
    return result


class CapacityAgent:
    def __init__(
        self,
        client: ModelClient,
        *,
        max_rounds=6,
        output_root: Path | None = None,
        secrets=(),
    ):
        self.client = client
        self.max_rounds = max_rounds
        self.output_root = output_root
        self.secrets = tuple(value for value in secrets if value)
        self.definitions = tool_definitions()
        self.validators = {
            tool["name"]: Draft202012Validator(tool["parameters"])
            for tool in self.definitions
        }
        self.instructions = system_prompt()
        self.reset()

    def reset(self):
        self.history = []
        self.results = {}
        self.baseline_enabled = False
        self.session_id = uuid4().hex[:12]
        self._counter = 0

    def _contains_secret(self, text):
        return any(secret in text for secret in self.secrets) or bool(
            re.search(r"\bsk-[A-Za-z0-9_-]{12,}", text)
        )

    def _invoke(self, name, raw):
        if name not in self.validators:
            return _error("unknown_tool", "Unknown tool / 未知工具")
        try:
            args = strict_json(raw)
            if self._contains_secret(raw) or not self.validators[name].is_valid(args):
                return _error(
                    "invalid_parameters", "Invalid tool arguments / 工具参数格式无效"
                )
            if name == "search_knowledge":
                data = search_knowledge(**args)
                if self._contains_secret(json.dumps(data, ensure_ascii=False)):
                    return _error(
                        "invalid_source", "Knowledge source rejected / 知识来源被拒绝"
                    )
                return {"ok": True, "data": data}
            if name == "generate_capacity_plot":
                stored = self.results.get(args["result_id"])
                kinds = {
                    "calculate_capacity": "capacity",
                    "compare_scenarios": "comparison",
                    "run_pue_sensitivity": "pue_sensitivity",
                }
                if stored is None or kinds.get(stored["tool"]) != args["analysis_type"]:
                    return _error(
                        "invalid_result",
                        "Use a matching calculation result_id / 请使用对应计算的 result_id",
                    )
                rows = [stored["result"]] if "result" in stored else stored["rows"]
                data = generate_capacity_plot(
                    {
                        "analysis_type": args["analysis_type"],
                        "result_data": rows,
                        "output_path": f"{self.session_id}/{uuid4().hex[:12]}.png",
                    },
                    output_root=self.output_root,
                )
                # Include the actual source identity without copying model-generated rows.
                data["source_result_id"] = args["result_id"]
                return {"ok": True, "data": data}
            step_source = None
            if name == "run_pue_sensitivity":
                if args["step"] is None:
                    if not self.baseline_enabled:
                        return _error(
                            "missing_parameters",
                            "Provide a sampling step or permit baseline defaults / 请提供采样步长或允许基准默认值",
                        )
                    settings = json.loads(
                        (ROOT / "data/sensitivity_parameters.json").read_text(
                            encoding="utf-8"
                        )
                    )
                    args["step"] = settings["pue"]["step"]
                    step_source = {
                        "origin": "scenario_assumption",
                        "source": "data/sensitivity_parameters.json",
                        "used_default": True,
                    }
                else:
                    step_source = {
                        "origin": "user_input",
                        "source": "request.step",
                        "used_default": False,
                    }
            if name == "compare_scenarios":
                scenarios = []
                for item in args["scenarios"]:
                    parameters = {
                        key: value
                        for key, value in item["parameters"].items()
                        if value is not None
                    }
                    if item["kind"] == "named":
                        if parameters or item["use_baseline_defaults"]:
                            return _error(
                                "invalid_parameters",
                                "Named scenarios cannot override parameters / 命名场景不能同时覆盖参数",
                            )
                        scenarios.append(item["name"])
                    else:
                        if item["use_baseline_defaults"] and not self.baseline_enabled:
                            return _error(
                                "defaults_not_authorized",
                                "Ask to use the baseline or supply missing fields / 请询问是否使用基准或补齐参数",
                            )
                        scenarios.append(
                            {
                                "name": item["name"],
                                "parameters": parameters,
                                "use_baseline_defaults": item["use_baseline_defaults"],
                            }
                        )
                args = {"scenarios": scenarios}
            else:
                if args["use_baseline_defaults"] and not self.baseline_enabled:
                    return _error(
                        "defaults_not_authorized",
                        "Ask to use the baseline or supply missing fields / 请询问是否使用基准或补齐参数",
                    )
                args["parameters"] = {
                    key: value
                    for key, value in args["parameters"].items()
                    if value is not None
                }
            response = dispatch_tool(name, args)
            if response["ok"]:
                self._counter += 1
                result_id = f"result_{self._counter}"
                data = response["data"]
                if step_source is not None:
                    data["sampling_step_source"] = step_source
                data["result_id"] = result_id
                self.results[result_id] = deepcopy(data)
            return response
        except (
            ValueError,
            TypeError,
            OverflowError,
            RecursionError,
            ToolValidationError,
        ):
            return _error(
                "invalid_parameters", "Tool arguments were rejected / 工具参数被拒绝"
            )
        except (OSError, ImportError):
            return _error(
                "tool_unavailable",
                "Tool output or dependency unavailable / 工具输出或依赖不可用",
            )

    def ask(self, question: str) -> TurnResult:
        if (
            not isinstance(question, str)
            or not question.strip()
            or len(question) > 12000
        ):
            return TurnResult(
                "Enter a shorter nonempty question.",
                "请输入非空且较短的问题。",
                status="error",
            )
        if self._contains_secret(question):
            return TurnResult(
                "Do not enter credentials in chat; configure them locally.",
                "不要在对话中输入凭据，请在本地配置。",
                status="error",
            )
        if len(self.results) >= 50 or len(json.dumps(self.history)) > 160000:
            return TurnResult(
                "Session is full. Use /reset to start a new conversation.",
                "会话已满，请输入 /reset 开始新会话。",
                status="error",
            )
        # Explicit baseline context persists until /reset or /baseline off.
        # 明确的基准上下文持续到 /reset 或 /baseline off。
        if re.search(
            r"(?:do not|don't|without|不要|不用|不使用|禁用).{0,30}(?:baseline|defaults|B200|基准|默认)",
            question,
            re.IGNORECASE,
        ):
            self.baseline_enabled = False
        elif re.search(
            r"baseline|\bB200\b|基准|使用默认|采用默认", question, re.IGNORECASE
        ):
            self.baseline_enabled = True
        start = len(self.history)
        self.history.append({"role": "user", "content": question})
        records, errors, executed = [], [], set()
        instructions = (
            self.instructions
            + f"\nBaseline defaults authorized by session: {self.baseline_enabled}"
        )
        try:
            for _ in range(self.max_rounds):
                reply = self.client.complete(
                    deepcopy(self.history), instructions, deepcopy(self.definitions)
                )
                if not reply.calls:
                    try:
                        final = strict_json(reply.text)
                        valid = Draft202012Validator(FINAL_SCHEMA).is_valid(final)
                        if valid:
                            valid = bool(
                                final["english"].strip() and final["chinese"].strip()
                            )
                            valid = valid and bool(
                                re.search(r"[\u4e00-\u9fff]", final["chinese"])
                            )
                            valid = valid and not self._contains_secret(reply.text)
                            # Quantitative prose is suppressed; tables use only tool values.
                            # 抑制包含数字的模型正文；表格只使用工具结果。
                            prose = final["english"] + final["chinese"]
                            valid = valid and not any(c.isdigit() for c in prose)
                            valid = valid and not re.search(
                                r"[零〇一二三四五六七八九十百千万亿壹贰叁肆伍陆柒捌玖拾佰仟]",
                                prose,
                            )
                            valid = valid and not re.search(
                                r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|hundred|thousand|million|billion)\b",
                                final["english"],
                                re.IGNORECASE,
                            )
                            valid = valid and (
                                final["kind"] != "answer"
                                or any(
                                    r["tool"]
                                    in {
                                        "calculate_capacity",
                                        "compare_scenarios",
                                        "run_pue_sensitivity",
                                        "generate_capacity_plot",
                                    }
                                    for r in records
                                )
                            )
                            valid = valid and (
                                final["kind"] != "knowledge"
                                or any(
                                    r.get("hits")
                                    for r in records
                                    if r["tool"] == "search_knowledge"
                                )
                            )
                            # Citation paths and URLs come only from the local retriever.
                            valid = valid and not re.search(
                                r"https?://|www\.|\[[^\]]+\]|\.md\b",
                                prose,
                                re.IGNORECASE,
                            )
                        if valid:
                            self.history.extend(
                                reply.history_items
                                or [{"role": "assistant", "content": reply.text}]
                            )
                            return TurnResult(
                                final["english"],
                                final["chinese"],
                                records,
                                errors,
                                final["kind"],
                            )
                    except (ValueError, TypeError, RecursionError):
                        pass
                    self.history.append(
                        {
                            "role": "developer",
                            "content": "Return valid bilingual qualitative JSON. No digits, numeric words, citation markers, URLs or paths. For kind=answer call a calculation tool; for kind=knowledge retrieve matching sources this turn. With no evidence ask a clarification or report unsupported scope. The host displays source excerpts and citations.",
                        }
                    )
                    continue
                if (
                    len(reply.calls) > 4
                    or len({c.call_id for c in reply.calls}) != len(reply.calls)
                    or any(
                        not call.call_id or call.call_id in executed
                        for call in reply.calls
                    )
                ):
                    raise ProviderError(
                        "Invalid or repeated tool call identifiers / 工具调用标识无效或重复"
                    )
                self.history.extend(
                    reply.history_items
                    or [
                        {
                            "type": "function_call",
                            "name": c.name,
                            "call_id": c.call_id,
                            "arguments": c.arguments,
                        }
                        for c in reply.calls
                    ]
                )
                for call in reply.calls:
                    executed.add(call.call_id)
                    response = self._invoke(call.name, call.arguments)
                    if response["ok"]:
                        records.append(deepcopy(response["data"]))
                    else:
                        errors.append(response["error"])
                    payload = (
                        {"ok": True, "data": _compact(response["data"])}
                        if response["ok"]
                        else response
                    )
                    self.history.append(
                        {
                            "type": "function_call_output",
                            "call_id": call.call_id,
                            "output": json.dumps(
                                payload, ensure_ascii=False, allow_nan=False
                            ),
                        }
                    )
        except ProviderError as exc:
            # Remove incomplete protocol items so a later user turn can retry cleanly.
            self.history = self.history[:start]
            self.history.append({"role": "user", "content": question})
            self.history.append(
                {
                    "role": "assistant",
                    "content": "Service interrupted. No completed conversational answer.",
                }
            )
            return TurnResult(
                "Model service unavailable. Computed results, if any, are shown below.",
                "模型服务暂不可用，已完成的计算结果会显示在下方。",
                records,
                errors
                + [
                    {
                        "code": "provider_error",
                        "message": "Model service error / 模型服务错误"
                        if self._contains_secret(str(exc))
                        else str(exc),
                    }
                ],
                "error",
            )
        self.history = self.history[:start]
        return TurnResult(
            "The tool loop limit was reached. Review computed results and try a narrower request.",
            "已达到工具循环上限，请查看已有结果并缩小问题范围后重试。",
            records,
            errors,
            "limited",
        )
