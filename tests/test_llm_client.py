"""Real SDK serialization over a local mock transport; no network calls.
通过本地模拟传输验证真实 SDK 序列化，不发送网络请求。
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx2
from openai import OpenAI

from agent.agent import CapacityAgent
from agent.demo import parameters
from agent.llm_client import ConfigurationError, OpenAIClient, ProviderError, Settings
from agent.tool_definitions import tool_definitions


def response(output, status="completed"):
    return {
        "id": "resp_test",
        "object": "response",
        "created_at": 0,
        "status": status,
        "output": output,
        "model": "test-model",
        "parallel_tool_calls": False,
        "tool_choice": "auto",
        "tools": [],
        "metadata": {},
    }


def message(text):
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "status": "completed",
        "content": [{"type": "output_text", "text": text, "annotations": []}],
    }


class LLMClientTests(unittest.TestCase):
    def client(self, handler):
        sdk = OpenAI(
            api_key="TEST_ONLY_FAKE_KEY",
            max_retries=0,
            http_client=httpx2.Client(transport=httpx2.MockTransport(handler)),
        )
        client = OpenAIClient(
            Settings("TEST_ONLY_FAKE_KEY", "test-model"), sdk_client=sdk
        )
        self.addCleanup(client.close)
        return client

    def test_actual_sdk_tool_roundtrip_and_reasoning_history(self):
        requests = []

        def handler(request):
            data = json.loads(request.content)
            requests.append(data)
            self.assertNotIn("TEST_ONLY_FAKE_KEY", request.content.decode())
            if len(requests) == 1:
                output = [
                    {
                        "id": "rs_test",
                        "type": "reasoning",
                        "summary": [],
                        "encrypted_content": "opaque-test-content",
                    },
                    {
                        "id": "fc_test",
                        "type": "function_call",
                        "call_id": "call_test",
                        "name": "calculate_capacity",
                        "arguments": json.dumps(
                            {
                                "parameters": parameters(facility_capacity_mw=500),
                                "use_baseline_defaults": True,
                            }
                        ),
                        "status": "completed",
                    },
                ]
            else:
                output = [
                    message(
                        json.dumps(
                            {
                                "kind": "answer",
                                "english": "Computed results are shown below.",
                                "chinese": "以下展示工具计算结果。",
                            }
                        )
                    )
                ]
            return httpx2.Response(200, json=response(output))

        turn = CapacityAgent(self.client(handler)).ask("Use baseline")
        self.assertEqual(turn.status, "answer")
        self.assertEqual(turn.records[0]["result"]["total_gpus"], 226304)
        self.assertFalse(requests[0]["store"])
        self.assertFalse(requests[0]["parallel_tool_calls"])
        self.assertEqual(requests[0]["text"]["format"]["type"], "json_schema")
        self.assertTrue(
            any(
                item.get("encrypted_content") == "opaque-test-content"
                for item in requests[1]["input"]
            )
        )
        outputs = [
            item
            for item in requests[1]["input"]
            if item.get("type") == "function_call_output"
        ]
        self.assertEqual(outputs[0]["call_id"], "call_test")
        self.assertEqual(
            json.loads(outputs[0]["output"])["data"]["result"]["max_pods"], 221
        )

    def test_api_status_errors_do_not_echo_remote_body(self):
        for status in (400, 401, 402, 403, 404, 429, 500):
            with self.subTest(status=status):
                client = self.client(
                    lambda request, status=status: httpx2.Response(
                        status, json={"error": {"message": "SENSITIVE_REMOTE_BODY"}}
                    )
                )
                with self.assertRaises(ProviderError) as context:
                    client.complete([], "test", tool_definitions())
                self.assertNotIn("SENSITIVE_REMOTE_BODY", str(context.exception))

    def test_timeout_and_connection_errors_are_sanitized(self):
        for exception in (httpx2.ReadTimeout, httpx2.ConnectError):

            def handler(request, exception=exception):
                raise exception("SENSITIVE_NETWORK_DETAIL", request=request)

            with (
                self.subTest(exception=exception),
                self.assertRaises(ProviderError) as context,
            ):
                self.client(handler).complete([], "test", tool_definitions())
            self.assertNotIn("SENSITIVE_NETWORK_DETAIL", str(context.exception))

    def test_incomplete_response_is_rejected(self):
        client = self.client(
            lambda request: httpx2.Response(200, json=response([], "incomplete"))
        )
        with self.assertRaises(ProviderError):
            client.complete([], "test", tool_definitions())

    def test_refusal_is_reported_without_untrusted_text(self):
        output = message("")
        output["content"] = [{"type": "refusal", "refusal": "SENSITIVE_REFUSAL"}]
        client = self.client(
            lambda request: httpx2.Response(200, json=response([output]))
        )
        with self.assertRaises(ProviderError) as context:
            client.complete([], "test", tool_definitions())
        self.assertNotIn("SENSITIVE_REFUSAL", str(context.exception))

    def test_dotenv_loading_precedence_and_key_repr(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text(
                "LLM_API_KEY=FILE_KEY\nLLM_MODEL=file-model\n", encoding="utf-8"
            )
            settings = Settings.load(
                root, {"LLM_API_KEY": "ENV_KEY", "LLM_MODEL": "env-model"}
            )
            self.assertEqual(settings.api_key, "ENV_KEY")
            self.assertEqual(settings.model, "env-model")
            self.assertNotIn("ENV_KEY", repr(settings))

    def test_missing_placeholder_and_invalid_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = {"LLM_API_KEY": "TEST_KEY", "LLM_MODEL": "test-model"}
            for change in (
                {"LLM_API_KEY": ""},
                {"LLM_API_KEY": "YOUR_API_KEY"},
                {"LLM_MODEL": "YOUR_MODEL_ID"},
                {"LLM_TIMEOUT_SECONDS": "NaN"},
                {"LLM_TIMEOUT_SECONDS": "0"},
                {"LLM_MAX_TOOL_ROUNDS": "999"},
                {"LLM_PROVIDER": "unsupported"},
            ):
                with self.subTest(change=change), self.assertRaises(ConfigurationError):
                    Settings.load(Path(tmp), {**base, **change})

    def test_openrouter_defaults_and_provider_specific_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings.load(
                Path(tmp),
                {
                    "LLM_PROVIDER": "openrouter",
                    "OPENROUTER_API_KEY": "ROUTER_KEY",
                    "OPENAI_API_KEY": "WRONG_PROVIDER_KEY",
                },
            )
            self.assertEqual(settings.model, "openrouter/free")
            self.assertEqual(settings.api_key, "ROUTER_KEY")
            self.assertFalse(settings.allow_paid_models)
            with self.assertRaises(ConfigurationError):
                Settings.load(
                    Path(tmp),
                    {
                        "LLM_PROVIDER": "openrouter",
                        "OPENAI_API_KEY": "WRONG_PROVIDER_KEY",
                    },
                )

    def test_openrouter_paid_models_require_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = {
                "LLM_PROVIDER": "openrouter",
                "LLM_API_KEY": "TEST_KEY",
                "LLM_MODEL": "vendor/model",
            }
            for change in ({}, {"LLM_ALLOW_PAID_MODELS": "yes"}):
                with self.assertRaises(ConfigurationError):
                    Settings.load(Path(tmp), {**base, **change})
            self.assertTrue(
                Settings.load(
                    Path(tmp), {**base, "LLM_ALLOW_PAID_MODELS": "true"}
                ).allow_paid_models
            )
            self.assertEqual(
                Settings.load(
                    Path(tmp), {**base, "LLM_MODEL": "vendor/model:free"}
                ).model,
                "vendor/model:free",
            )

    def test_openrouter_sdk_endpoint_and_tool_roundtrip(self):
        requests = []

        def handler(request):
            self.assertEqual(str(request.url), "https://openrouter.ai/api/v1/responses")
            self.assertEqual(request.headers["authorization"], "Bearer TEST_ROUTER_KEY")
            data = json.loads(request.content)
            requests.append(data)
            self.assertEqual(data["model"], "openrouter/free")
            self.assertNotIn("include", data)
            self.assertEqual(
                data["provider"],
                {
                    "max_price": {"prompt": 0, "completion": 0},
                },
            )
            self.assertEqual(len(data["tools"]), 5)
            self.assertNotIn("text", data)
            self.assertIn("JSON object", data["instructions"])
            self.assertEqual(data["reasoning"], {"effort": "low"})
            if len(requests) == 1:
                output = [
                    {
                        "type": "function_call",
                        "id": "fc_router",
                        "call_id": "call_router",
                        "name": "calculate_capacity",
                        "arguments": json.dumps(
                            {
                                "parameters": parameters(facility_capacity_mw=500),
                                "use_baseline_defaults": True,
                            }
                        ),
                    }
                ]
            else:
                result = next(
                    item
                    for item in data["input"]
                    if item.get("type") == "function_call_output"
                )
                self.assertEqual(result["call_id"], "call_router")
                self.assertEqual(
                    json.loads(result["output"])["data"]["result"]["total_gpus"], 226304
                )
                output = [
                    message(
                        json.dumps(
                            {
                                "kind": "answer",
                                "english": "Computed results follow.",
                                "chinese": "以下为计算结果。",
                            }
                        )
                    )
                ]
            return httpx2.Response(200, json=response(output))

        def sdk_factory(**kwargs):
            return OpenAI(
                **kwargs,
                http_client=httpx2.Client(transport=httpx2.MockTransport(handler)),
            )

        with patch("openai.OpenAI", side_effect=sdk_factory):
            client = OpenAIClient(
                Settings("TEST_ROUTER_KEY", "openrouter/free", provider="openrouter")
            )
        self.addCleanup(client.close)
        turn = CapacityAgent(client).ask("Use baseline")
        self.assertEqual(turn.status, "answer")
        self.assertEqual(len(requests), 2)
        self.assertEqual(turn.records[0]["result"]["max_pods"], 221)
