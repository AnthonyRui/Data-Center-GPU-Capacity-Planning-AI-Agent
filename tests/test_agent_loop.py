"""Offline orchestration tests; they do not validate live model understanding.
离线编排测试，不代表真实模型的自然语言理解验证。
"""

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

from agent.agent import CapacityAgent
from agent.demo import QUESTIONS, DemoClient, parameters
from agent.llm_client import ModelReply, ProviderError, ToolCall
from agent.presentation import format_turn
from agent.tool_definitions import tool_definitions
from src.power_model import ModelInputs, evaluate


def final(
    kind="answer",
    english="Computed results are shown below.",
    chinese="以下展示工具计算结果。",
):
    return ModelReply(
        text=json.dumps(
            {"kind": kind, "english": english, "chinese": chinese}, ensure_ascii=False
        )
    )


def capacity(call_id="c1", **values):
    return ModelReply(
        calls=[
            ToolCall(
                call_id,
                "calculate_capacity",
                json.dumps(
                    {
                        "parameters": parameters(**values),
                        "use_baseline_defaults": True,
                    }
                ),
            )
        ]
    )


class ScriptedClient:
    def __init__(self, replies):
        self.replies, self.requests = list(replies), []

    def complete(self, history, instructions, tools):
        self.requests.append(deepcopy(history))
        value = self.replies.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


class AgentLoopTests(unittest.TestCase):
    def test_five_required_scenario_workflows_offline(self):
        for case in QUESTIONS:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                agent = CapacityAgent(DemoClient(case), output_root=Path(tmp))
                turn = agent.ask(QUESTIONS[case])
                self.assertEqual(
                    turn.status, "unsupported" if case == "unsupported" else "answer"
                )
                self.assertFalse(turn.errors)
                if case == "baseline":
                    self.assertEqual(turn.records[0]["result"], evaluate(ModelInputs()))
                if case == "custom":
                    self.assertEqual(turn.records[0]["result"]["max_pods"], 127)
                if case == "comparison":
                    self.assertEqual(
                        [r["total_gpus"] for r in turn.records[0]["rows"]],
                        [236544, 226304, 208896],
                    )
                if case == "sensitivity":
                    self.assertEqual(turn.records[0]["summary"]["sample_count"], 51)
                    self.assertEqual(
                        turn.records[0]["sampling_step_source"]["origin"],
                        "scenario_assumption",
                    )
                    self.assertTrue(Path(turn.records[1]["saved_png_path"]).is_file())
                if case == "unsupported":
                    self.assertEqual(turn.records, [])

    def test_all_definitions_strict_and_plot_takes_only_result_id(self):
        definitions = tool_definitions()
        self.assertEqual(len(definitions), 4)

        def check(schema):
            if schema.get("type") == "object":
                self.assertFalse(schema["additionalProperties"])
                self.assertEqual(set(schema["required"]), set(schema["properties"]))
                for child in schema["properties"].values():
                    check(child)
            if schema.get("type") == "array":
                check(schema["items"])

        for definition in definitions:
            Draft202012Validator.check_schema(definition["parameters"])
            self.assertTrue(definition["strict"])
            check(definition["parameters"])
        self.assertEqual(
            set(definitions[-1]["parameters"]["properties"]),
            {"analysis_type", "result_id"},
        )

    def test_missing_defaults_require_clarification_then_followup(self):
        client = ScriptedClient(
            [
                capacity(),
                final(
                    "clarification",
                    "May I use the documented baseline?",
                    "是否允许使用文档中的基准默认值？",
                ),
                capacity("c2"),
                final(),
            ]
        )
        agent = CapacityAgent(client)
        first = agent.ask("Plan a deployment.")
        self.assertEqual(first.status, "clarification")
        self.assertEqual(first.errors[0]["code"], "defaults_not_authorized")
        second = agent.ask("Use the baseline.")
        self.assertEqual(second.records[0]["result"]["max_pods"], 221)
        self.assertTrue(
            any(
                item.get("content") == "Plan a deployment."
                for item in client.requests[-1]
            )
        )

    def test_explicit_default_rejection_disables_session(self):
        client = ScriptedClient(
            [
                capacity(),
                final(
                    "clarification",
                    "Please supply the missing specifications.",
                    "请提供缺少的设备参数。",
                ),
            ]
        )
        agent = CapacityAgent(client)
        agent.baseline_enabled = True
        turn = agent.ask("Do not use baseline defaults.")
        self.assertFalse(agent.baseline_enabled)
        self.assertEqual(turn.errors[0]["code"], "defaults_not_authorized")

    def test_invalid_parameters_are_not_silently_corrected(self):
        agent = CapacityAgent(
            ScriptedClient(
                [
                    capacity(pue=0.9),
                    final(
                        "clarification",
                        "Please provide a valid PUE.",
                        "请提供有效的 PUE。",
                    ),
                ]
            )
        )
        turn = agent.ask("Use baseline with PUE .9")
        self.assertFalse(turn.records)
        self.assertEqual(turn.errors[0]["code"], "invalid_parameters")

    def test_malformed_duplicate_and_nonfinite_json_is_rejected(self):
        for raw in ("not JSON", '{"a":1,"a":2}', '{"pue":NaN}', "[]"):
            with self.subTest(raw=raw):
                agent = CapacityAgent(ScriptedClient([]))
                result = agent._invoke("calculate_capacity", raw)
                self.assertFalse(result["ok"])

    def test_unknown_tool_and_duplicate_call_id_are_bounded(self):
        client = ScriptedClient(
            [
                ModelReply(calls=[ToolCall("x", "shell", "{}")]),
                final("unsupported", "This action is unsupported.", "不支持该操作。"),
            ]
        )
        turn = CapacityAgent(client).ask("Execute a shell command")
        self.assertEqual(turn.errors[0]["code"], "unknown_tool")
        client = ScriptedClient([capacity(), capacity()])
        turn = CapacityAgent(client).ask("Use baseline")
        self.assertEqual(len(turn.records), 1)
        self.assertEqual(turn.status, "error")

    def test_infinite_tool_request_stops_at_limit(self):
        client = ScriptedClient([capacity("a"), capacity("b")])
        turn = CapacityAgent(client, max_rounds=2).ask("Use baseline")
        self.assertEqual(turn.status, "limited")
        self.assertEqual(len(client.requests), 2)

    def test_numeric_or_malformed_model_answers_are_not_shown(self):
        for reply in [
            final(english="999999 GPUs", chinese="有很多 GPU。"),
            final(english="one million GPUs", chinese="有很多 GPU。"),
            ModelReply(text="broken"),
        ]:
            with self.subTest(reply=reply):
                client = ScriptedClient([capacity(), reply, final()])
                turn = CapacityAgent(client).ask("Use baseline")
                text = format_turn(turn)
                self.assertEqual(turn.status, "answer")
                self.assertIn("226304", text)
                self.assertNotIn("999999", text)
                self.assertNotIn("one million", text)

    def test_answer_without_calculation_is_rejected(self):
        client = ScriptedClient(
            [
                final(),
                final(
                    "clarification",
                    "Which configuration should I calculate?",
                    "需要计算哪种配置？",
                ),
            ]
        )
        turn = CapacityAgent(client).ask("How many GPUs?")
        self.assertEqual(turn.status, "clarification")

    def test_provider_error_preserves_finished_results_and_allows_retry(self):
        client = ScriptedClient(
            [
                capacity(),
                ProviderError("Model timed out / 模型超时"),
                capacity("b"),
                final(),
            ]
        )
        agent = CapacityAgent(client)
        first = agent.ask("Use baseline")
        self.assertEqual(first.status, "error")
        self.assertEqual(first.records[0]["result"]["max_pods"], 221)
        second = agent.ask("Try again")
        self.assertEqual(second.status, "answer")
        self.assertFalse(
            any(
                item.get("type") == "function_call_output"
                for item in client.requests[2]
            )
        )

    def test_secrets_never_reach_provider_or_presentation(self):
        secret = "TEST_PRIVATE_CREDENTIAL_ABCDEF"
        client = ScriptedClient([])
        agent = CapacityAgent(client, secrets=(secret,))
        turn = agent.ask("My key is " + secret)
        self.assertEqual(client.requests, [])
        self.assertNotIn(secret, format_turn(turn))
        client = ScriptedClient([ProviderError(secret)])
        turn = CapacityAgent(client, secrets=(secret,)).ask("Use baseline")
        self.assertNotIn(secret, format_turn(turn))

    def test_plot_requires_existing_matching_result(self):
        agent = CapacityAgent(ScriptedClient([]))
        with patch("agent.agent.generate_capacity_plot") as plot:
            for args in (
                {"result_id": "fake", "analysis_type": "capacity"},
                {"result_id": "fake", "analysis_type": "capacity", "result_data": []},
            ):
                self.assertFalse(
                    agent._invoke("generate_capacity_plot", json.dumps(args))["ok"]
                )
            plot.assert_not_called()

    def test_prompt_sends_compact_rows_but_retains_full_plot_data(self):
        agent = CapacityAgent(DemoClient("sensitivity"))
        with tempfile.TemporaryDirectory() as tmp:
            agent.output_root = Path(tmp)
            turn = agent.ask(QUESTIONS["sensitivity"])
        self.assertEqual(len(agent.results["result_1"]["rows"]), 51)
        payload = next(
            strict
            for item in agent.history
            if item.get("type") == "function_call_output"
            for strict in [json.loads(item["output"])]
            if "rows" in strict.get("data", {})
        )
        self.assertEqual(len(payload["data"]["rows"]), 12)
        self.assertTrue(payload["data"]["rows_truncated"])
        self.assertEqual(turn.records[1]["source_result_id"], "result_1")

    def test_reset_removes_history_results_and_default_permission(self):
        agent = CapacityAgent(DemoClient("baseline"))
        agent.ask(QUESTIONS["baseline"])
        old_session = agent.session_id
        agent.reset()
        self.assertEqual(agent.history, [])
        self.assertEqual(agent.results, {})
        self.assertFalse(agent.baseline_enabled)
        self.assertNotEqual(agent.session_id, old_session)

    def test_presentation_contains_sources_and_bilingual_sections(self):
        turn = CapacityAgent(DemoClient("baseline")).ask(QUESTIONS["baseline"])
        text = format_turn(turn)
        self.assertLess(text.index("English"), text.index("中文"))
        self.assertIn("user input / 用户输入", text)
        self.assertIn("documented public specification", text)
        self.assertIn("scenario assumption", text)
        self.assertIn("[default / 默认值]", text)
