"""Reject invalid requests at the tool boundary. / 在工具边界拒绝非法请求。"""

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict

from agent import (
    calculate_capacity,
    compare_scenarios,
    dispatch_tool,
    run_pue_sensitivity,
)
from agent.schemas import (
    CapacityRequest,
    MissingParametersError,
    PueSensitivityRequest,
    ToolValidationError,
)
from src.power_model import ModelInputs


class AgentParameterValidationTests(unittest.TestCase):
    def test_invalid_model_parameters(self):
        invalid = {
            "facility_capacity_mw": [
                0,
                -1,
                True,
                "500",
                None,
                float("nan"),
                float("inf"),
                10**1000,
            ],
            "server_power_kw": [0, -1, False, "14.3", float("-inf")],
            "network_power_kw": [-0.01, True, None],
            "gpus_per_server": [0, -1, 2.5, 8.0, True, "8"],
            "servers_per_rack": [0, -1, 4.1, 4.0, False],
            "racks_per_pod": [0, -1, 32.5, 32.0, True],
            "pue": [0.99, 0, -1, True, float("nan"), float("inf")],
        }
        for name, values in invalid.items():
            for value in values:
                with (
                    self.subTest(name=name, value=value),
                    self.assertRaises(ToolValidationError),
                ):
                    calculate_capacity(
                        {"parameters": {name: value}, "use_baseline_defaults": True}
                    )

    def test_missing_parameters_require_explicit_opt_in(self):
        with self.assertRaises(MissingParametersError) as context:
            calculate_capacity({"parameters": {"facility_capacity_mw": 300}})
        self.assertIn("server_power_kw", context.exception.missing_fields)
        self.assertNotIn("facility_capacity_mw", context.exception.missing_fields)
        response = dispatch_tool("calculate_capacity", {})
        self.assertEqual(response["error"]["code"], "missing_parameters")
        self.assertEqual(
            set(response["error"]["missing_fields"]), set(asdict(ModelInputs()))
        )

    def test_null_is_not_treated_as_missing(self):
        with self.assertRaises(ToolValidationError):
            calculate_capacity(
                {"parameters": {"pue": None}, "use_baseline_defaults": True}
            )

    def test_default_flag_requires_boolean(self):
        for value in (1, 0, "true", None, []):
            with self.subTest(value=value), self.assertRaises(ToolValidationError):
                calculate_capacity({"use_baseline_defaults": value})

    def test_unknown_fields_and_wrong_shapes(self):
        requests = [
            None,
            [],
            "text",
            12,
            {"unknown": 1},
            {"parameters": []},
            {"parameters": {"facility_capacity_kw": 500}},
            {"parameters": {1: 2}},
        ]
        for request in requests:
            with self.subTest(request=request), self.assertRaises(ToolValidationError):
                calculate_capacity(request)

    def test_mutated_dataclass_is_revalidated(self):
        request = CapacityRequest(parameters=asdict(ModelInputs()))
        request.parameters["pue"] = 0.9
        with self.assertRaises(ToolValidationError):
            calculate_capacity(request)

    def test_invalid_scenario_requests(self):
        cases = [
            {},
            {"scenarios": []},
            {"scenarios": ["Baseline"]},
            {"scenarios": ["Baseline"] * 51},
            {"scenarios": ["Baseline", "Baseline"]},
            {"scenarios": ["Baseline", "unknown"]},
            {"scenarios": "Baseline"},
            {"scenarios": ["Baseline", 1]},
            {"scenarios": ["Baseline", {}]},
            {"scenarios": ["Baseline", {"name": "custom", "extra": 1}]},
            {"scenarios": ["Baseline", {"name": "custom", "parameters": {"pue": 0.9}}]},
            {"scenarios": ["Baseline", {"name": "\n"}]},
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ToolValidationError):
                compare_scenarios(case)

    def test_partial_custom_scenario_needs_opt_in(self):
        with self.assertRaises(MissingParametersError):
            compare_scenarios(
                {
                    "scenarios": [
                        "Baseline",
                        {"name": "Custom", "parameters": {"pue": 1.3}},
                    ]
                }
            )

    def test_invalid_pue_ranges_and_ambiguous_pue(self):
        base = {
            "pue_start": 1.1,
            "pue_end": 1.6,
            "step": 0.01,
            "use_baseline_defaults": True,
        }
        changes = [
            {"pue_start": 0.9},
            {"pue_end": 1.0},
            {"step": 0},
            {"step": -0.1},
            {"step": float("nan")},
            {"step": float("inf")},
            {"step": True},
            {"pue_start": "1.1"},
            {"pue_end": float("inf")},
            {"step": 1e-10},
            {"parameters": {"pue": 1.2}},
            {"parameters": {"servers_per_rack": 2.5}},
        ]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ToolValidationError):
                run_pue_sensitivity({**base, **change})
        with self.assertRaises(ToolValidationError):
            run_pue_sensitivity({"pue_start": 1.1, "pue_end": 1.6})

    def test_sweep_limit_and_float_resolution(self):
        request = PueSensitivityRequest(pue_start=1, pue_end=1.9999, step=0.0001)
        self.assertEqual(len(request.values()), 10000)
        with self.assertRaises(ToolValidationError):
            PueSensitivityRequest(pue_start=1, pue_end=2, step=0.0001)
        with self.assertRaises(ToolValidationError):
            PueSensitivityRequest(
                pue_start=1, pue_end=1.000000000000001, step=1e-17
            ).values()

    def test_numeric_overflow_returns_controlled_error(self):
        response = dispatch_tool(
            "calculate_capacity",
            {
                "parameters": {
                    "server_power_kw": 1e308,
                    "servers_per_rack": 100,
                },
                "use_baseline_defaults": True,
            },
        )
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "invalid_parameters")

    def test_unknown_tools_fail_without_execution(self):
        for name in (
            "shell",
            "__import__",
            "calculate_capacity; echo test",
            "",
            None,
            [],
        ):
            with self.subTest(name=name):
                response = dispatch_tool(name, {})
                self.assertFalse(response["ok"])
                self.assertEqual(response["error"]["code"], "unknown_tool")

    def test_error_responses_and_output_do_not_echo_supplied_secrets(self):
        fake_secret = "TEST_ONLY_SENSITIVE_VALUE_123"
        stream = io.StringIO()
        with redirect_stdout(stream), redirect_stderr(stream):
            responses = [
                dispatch_tool(fake_secret, {}),
                dispatch_tool("calculate_capacity", {fake_secret: "x"}),
                dispatch_tool(
                    "calculate_capacity", {"parameters": {"pue": fake_secret}}
                ),
                dispatch_tool(
                    "compare_scenarios", {"scenarios": ["Baseline", fake_secret]}
                ),
                dispatch_tool("calculate_capacity", fake_secret),
            ]
        self.assertNotIn(fake_secret, json.dumps(responses))
        self.assertEqual(stream.getvalue(), "")
        self.assertTrue(all(not response["ok"] for response in responses))
