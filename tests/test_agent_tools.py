"""Numerical equivalence and provenance. / 数值一致性与参数来源。"""

import json
import tempfile
import unittest
from dataclasses import asdict, replace
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from agent import (
    calculate_capacity,
    compare_scenarios,
    dispatch_tool,
    run_pue_sensitivity,
)
from agent.schemas import CapacityRequest
from src.power_model import ModelInputs, evaluate
from src.scenarios import evaluate_scenarios
from src.sensitivity import run_sensitivity

ROOT = Path(__file__).resolve().parents[1]


class AgentToolTests(unittest.TestCase):
    def test_baseline_exactly_matches_direct_model(self):
        result = calculate_capacity(CapacityRequest(use_baseline_defaults=True))
        self.assertEqual(result["result"], evaluate(ModelInputs()))
        self.assertEqual(result["result"]["max_pods"], 221)
        self.assertEqual(result["result"]["total_racks"], 7072)
        self.assertEqual(result["result"]["total_gpus"], 226304)
        self.assertEqual(result["result"]["remaining_capacity_mw"], 1.84832)
        self.assertEqual(result["result"]["capacity_utilization_pct"], 99.630336)

    def test_explicit_custom_capacity_and_no_input_mutation(self):
        request = {
            "parameters": {
                "facility_capacity_mw": 300,
                "pue": 1.25,
                "servers_per_rack": 4,
                "racks_per_pod": 32,
            },
            "use_baseline_defaults": True,
        }
        before = json.dumps(request)
        response = calculate_capacity(request)
        self.assertEqual(
            response["result"],
            evaluate(replace(ModelInputs(), facility_capacity_mw=300, pue=1.25)),
        )
        self.assertEqual(response["result"]["max_pods"], 127)
        self.assertEqual(response["result"]["remaining_capacity_mw"], 1.804)
        self.assertEqual(json.dumps(request), before)
        self.assertEqual(
            set(response["assumptions_used"]),
            {"server_power_kw", "gpus_per_server", "network_power_kw"},
        )

    def test_full_explicit_inputs_need_no_default_catalog(self):
        with patch(
            "agent.tools._catalog",
            side_effect=AssertionError("Should not load defaults"),
        ):
            response = calculate_capacity({"parameters": asdict(ModelInputs())})
        self.assertEqual(response["assumptions_used"], [])
        self.assertTrue(
            all(s["origin"] == "user_input" for s in response["provenance"].values())
        )

    def test_sources_distinguish_public_specs_assumptions_and_user_values(self):
        response = calculate_capacity(
            {"parameters": {"pue": 1.25}, "use_baseline_defaults": True}
        )
        sources = response["provenance"]
        self.assertEqual(sources["server_power_kw"]["origin"], "public_specification")
        self.assertEqual(sources["racks_per_pod"]["origin"], "scenario_assumption")
        self.assertEqual(sources["pue"]["origin"], "user_input")
        self.assertFalse(sources["pue"]["used_default"])
        self.assertTrue(sources["server_power_kw"]["used_default"])

    def test_defaults_follow_csv_and_edited_power_is_not_public_spec(self):
        frame = pd.read_csv(ROOT / "data/scenario_parameters.csv")
        frame.loc[frame.scenario == "Baseline", "facility_capacity_mw"] = 400
        frame.loc[frame.scenario == "Baseline", "server_power_kw"] = 15
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scenarios.csv"
            frame.to_csv(path, index=False)
            with patch("agent.tools.SCENARIO_PATH", path):
                response = calculate_capacity({"use_baseline_defaults": True})
        self.assertEqual(
            response["result"],
            evaluate(
                replace(ModelInputs(), facility_capacity_mw=400, server_power_kw=15)
            ),
        )
        self.assertEqual(
            response["provenance"]["server_power_kw"]["origin"], "scenario_assumption"
        )
        self.assertEqual(ModelInputs().facility_capacity_mw, 500)

    def test_named_scenarios_exactly_match_existing_scenario_logic(self):
        names = ["Conservative", "Baseline", "High-Density"]
        response = compare_scenarios({"scenarios": names})
        expected = evaluate_scenarios(ROOT / "data/scenario_parameters.csv").to_dict(
            "records"
        )
        self.assertEqual(response["rows"], expected)
        self.assertEqual(
            response["rows"][0]["input_status"], "reconstructed_assumption"
        )
        self.assertEqual(
            response["rows"][2]["input_status"], "reconstructed_assumption"
        )
        self.assertEqual(
            response["tradeoffs"]["total_gpus"]["maximum_scenarios"], ["High-Density"]
        )
        self.assertEqual(
            response["tradeoffs"]["max_pods"]["maximum_scenarios"], ["Conservative"]
        )

    def test_custom_pue_comparison_and_ties(self):
        response = compare_scenarios(
            {
                "scenarios": [
                    {
                        "name": str(pue),
                        "parameters": {"pue": pue},
                        "use_baseline_defaults": True,
                    }
                    for pue in (1.15, 1.2, 1.3)
                ]
            }
        )
        self.assertEqual(
            [r["total_gpus"] for r in response["rows"]], [236544, 226304, 208896]
        )
        tied = compare_scenarios(
            {
                "scenarios": [
                    "Baseline",
                    {
                        "name": "Same",
                        "parameters": asdict(ModelInputs()),
                    },
                ]
            }
        )
        self.assertEqual(
            tied["tradeoffs"]["total_gpus"]["maximum_scenarios"], ["Baseline", "Same"]
        )
        self.assertEqual(
            tied["tradeoffs"]["total_gpus"]["minimum_scenarios"], ["Baseline", "Same"]
        )

    def test_pue_sweep_exactly_matches_existing_sensitivity(self):
        response = run_pue_sensitivity(
            {
                "pue_start": 1.1,
                "pue_end": 1.6,
                "step": 0.01,
                "use_baseline_defaults": True,
            }
        )
        expected = run_sensitivity(
            ModelInputs(), ROOT / "data/sensitivity_parameters.json"
        )["pue"].to_dict("records")
        self.assertEqual(response["rows"], expected)
        self.assertEqual(response["summary"]["sample_count"], 51)
        self.assertEqual(
            response["summary"]["total_gpus"],
            {
                "minimum": 169984,
                "maximum": 246784,
                "first": 246784,
                "last": 169984,
            },
        )
        self.assertNotIn("pue", response["assumptions_used"])
        frame = pd.DataFrame(response["rows"])
        self.assertTrue(frame.total_gpus.is_monotonic_decreasing)
        self.assertTrue((frame.remaining_capacity_mw >= 0).all())
        self.assertTrue(
            (frame.remaining_capacity_mw < frame.pod_facility_power_mw).all()
        )

    def test_pue_non_aligned_end_and_single_point(self):
        response = run_pue_sensitivity(
            {
                "pue_start": 1.1,
                "pue_end": 1.2,
                "step": 0.03,
                "use_baseline_defaults": True,
            }
        )
        self.assertEqual([r["pue"] for r in response["rows"]], [1.1, 1.13, 1.16, 1.19])
        self.assertEqual(response["range"]["actual_end"], 1.19)
        one = run_pue_sensitivity(
            {
                "pue_start": 1.2,
                "pue_end": 1.2,
                "step": 0.1,
                "use_baseline_defaults": True,
            }
        )
        self.assertEqual(one["summary"]["sample_count"], 1)
        self.assertEqual(one["rows"][0]["total_gpus"], 226304)

    def test_custom_sweep_needs_no_redundant_baseline_pue(self):
        parameters = asdict(ModelInputs())
        parameters.pop("pue")
        response = run_pue_sensitivity(
            {"parameters": parameters, "pue_start": 1.2, "pue_end": 1.3, "step": 0.1}
        )
        self.assertEqual(response["assumptions_used"], [])
        self.assertEqual([r["max_pods"] for r in response["rows"]], [221, 204])

    def test_decimal_floor_boundary_and_zero_deployments(self):
        response = calculate_capacity(
            {
                "parameters": {
                    "facility_capacity_mw": 0.3,
                    "server_power_kw": 100,
                    "gpus_per_server": 1,
                    "servers_per_rack": 1,
                    "network_power_kw": 0,
                    "racks_per_pod": 1,
                    "pue": 1,
                }
            }
        )
        self.assertEqual(response["result"]["max_pods"], 3)
        self.assertEqual(response["result"]["remaining_capacity_mw"], 0)
        small = calculate_capacity(
            {"parameters": {"facility_capacity_mw": 1}, "use_baseline_defaults": True}
        )
        self.assertEqual(small["result"]["total_gpus"], 0)
        self.assertEqual(small["result"]["remaining_capacity_mw"], 1)

    def test_results_are_json_serializable_with_bilingual_explanations_and_units(self):
        responses = [
            calculate_capacity({"use_baseline_defaults": True}),
            compare_scenarios({"scenarios": ["Baseline", "Conservative"]}),
            run_pue_sensitivity(
                {
                    "pue_start": 1.1,
                    "pue_end": 1.2,
                    "step": 0.01,
                    "use_baseline_defaults": True,
                }
            ),
        ]
        for response in responses:
            with self.subTest(tool=response["tool"]):
                self.assertEqual(
                    json.loads(json.dumps(response, allow_nan=False)), response
                )
                self.assertEqual(list(response["explanation"]), ["en", "zh"])
                self.assertEqual(response["units"]["remaining_capacity_mw"], "MW")

    def test_dispatcher_returns_structured_success(self):
        result = dispatch_tool("calculate_capacity", {"use_baseline_defaults": True})
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["result"], evaluate(ModelInputs()))
