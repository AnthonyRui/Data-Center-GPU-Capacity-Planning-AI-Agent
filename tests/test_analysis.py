"""Scenario provenance, rounding and input validation. / 场景来源、舍入和输入验证。"""
import tempfile
import unittest
from pathlib import Path
import pandas as pd
from src.scenarios import evaluate_scenarios, compare_references, load_scenarios
from src.sensitivity import run_sensitivity
from src.power_model import ModelInputs

ROOT = Path(__file__).resolve().parents[1]


class AnalysisTests(unittest.TestCase):
    def test_reconstructed_outputs_match_reference_precision(self):
        results = evaluate_scenarios(ROOT / "data/scenario_parameters.csv")
        comparison = compare_references(results, ROOT / "data/original_scenario_references.csv")
        self.assertEqual(len(comparison), 15)
        self.assertTrue(comparison.matches_display_precision.all())
        self.assertEqual(results.input_status.tolist().count("reconstructed_assumption"), 2)
        self.assertEqual(results.max_pods.tolist(), [377, 221, 184])

    def test_csv_fractional_count_is_not_truncated(self):
        frame = pd.read_csv(ROOT / "data/scenario_parameters.csv")
        frame["racks_per_pod"] = frame["racks_per_pod"].astype(float)
        frame.loc[0, "racks_per_pod"] = 24.5
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            frame.to_csv(path, index=False)
            with self.assertRaises(ValueError):
                load_scenarios(path)

    def test_sweep_ranges_and_feasibility(self):
        sweeps = run_sensitivity(ModelInputs(), ROOT / "data/sensitivity_parameters.json")
        p = sweeps["pue"]
        self.assertEqual(len(p), 51)
        self.assertEqual(p.pue.iloc[0], 1.1)
        self.assertEqual(p.pue.iloc[-1], 1.6)
        self.assertTrue(p.total_gpus.is_monotonic_decreasing)
        for frame in sweeps.values():
            self.assertTrue((frame.remaining_capacity_mw >= 0).all())
            self.assertTrue((frame.remaining_capacity_mw < frame.pod_facility_power_mw).all())
