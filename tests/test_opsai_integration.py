"""Application boundary: preserve model values, evidence and actionable errors."""

import json
import subprocess
import sys
import unittest
from dataclasses import asdict
from pathlib import Path

from examples.opsai_capacity import capacity_panel
from src.power_model import ModelInputs, evaluate

ROOT = Path(__file__).resolve().parents[1]


class OpsAIIntegrationTests(unittest.TestCase):
    def test_application_preserves_baseline_and_custom_results(self):
        for inputs in (ModelInputs(), ModelInputs(facility_capacity_mw=300, pue=1.25)):
            with self.subTest(inputs=inputs):
                result = capacity_panel(asdict(inputs))
                self.assertTrue(result["ok"])
                data = result["data"]
                self.assertEqual(data["result"], evaluate(inputs))
                self.assertEqual(data["assumptions_used"], [])
                self.assertEqual(data["units"]["remaining_capacity_mw"], "MW")
                self.assertTrue(all(p["origin"] == "user_input"
                                    for p in data["provenance"].values()))

    def test_application_preserves_validation_and_default_policy(self):
        missing = capacity_panel({})
        self.assertFalse(missing["ok"])
        self.assertEqual(missing["error"]["code"], "missing_parameters")
        self.assertIn("pue", missing["error"]["missing_fields"])
        invalid = capacity_panel({"pue": 0.9}, use_baseline_defaults=True)
        self.assertFalse(invalid["ok"])
        self.assertEqual(invalid["error"]["code"], "invalid_parameters")
        baseline = capacity_panel({}, use_baseline_defaults=True)["data"]
        self.assertEqual(baseline["result"]["total_gpus"], 226304)
        self.assertIn("pue", baseline["assumptions_used"])

    def test_example_runs_without_llm_or_network_from_other_directory(self):
        # Fresh interpreter: fail any attempt to load an LLM adapter or use sockets.
        script = '''
import runpy, socket, sys
class BlockLLM:
    def find_spec(self, fullname, path=None, target=None):
        if fullname in {"openai", "dotenv", "agent.llm_client"}:
            raise AssertionError("LLM dependency loaded")
sys.meta_path.insert(0, BlockLLM())
def blocked(*args, **kwargs):
    raise AssertionError("Network attempted")
socket.socket = blocked
runpy.run_path(sys.argv[1], run_name="__main__")
'''
        run = subprocess.run(
            [sys.executable, "-X", "utf8", "-c", script, str(ROOT / "examples/opsai_capacity.py")],
            cwd=ROOT.parent, capture_output=True, text=True, encoding="utf-8",
            timeout=60, check=False,
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        result = json.loads(run.stdout)["data"]["result"]
        self.assertEqual(result["max_pods"], 221)
        self.assertEqual(result["remaining_capacity_mw"], 1.84832)
