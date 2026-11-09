import json
import tempfile
import unittest
from pathlib import Path

from agent import compare_allocations, dispatch_tool
from agent.agent import CapacityAgent
from agent.allocation_charts import chart_data
from agent.demo import parameters
from src.allocation import allocation_plans
from src.power_model import ModelInputs


class RackConstraintTests(unittest.TestCase):
    def test_independent_limits_ties_zero_and_reserves(self):
        # Each rack consumes 1 MW, with four racks per pod.
        cfg = ModelInputs(
            facility_capacity_mw=10,
            server_power_kw=1000,
            servers_per_rack=1,
            network_power_kw=0,
            pue=1,
            racks_per_pod=4,
        )
        for cap, reason, racks in [
            (None, "power", 9),
            (10, "power", 9),
            (9, "both", 9),
            (7, "rack_space", 7),
            (0, "rack_space", 0),
        ]:
            a = allocation_plans(cfg, 10, rack_limit=cap)
            self.assertEqual(
                (a["limiting_constraint"], a["feasible_racks"]), (reason, racks)
            )
            for name, used in [("partial_pod", racks), ("whole_pod", racks // 4 * 4)]:
                p = a[name]
                self.assertEqual(p["total_racks"], used)
                self.assertEqual(
                    p["used_facility_mw"]
                    + p["space_limited_unused_mw"]
                    + p["packing_remainder_mw"],
                    9,
                )
            self.assertEqual(a["whole_pod"]["space_limited_unused_mw"], 9 - racks)
        for cap in (-1, True, 1.5, "7"):
            self.assertFalse(
                dispatch_tool(
                    "compare_allocations",
                    {"use_baseline_defaults": True, "rack_limit": cap},
                )["ok"]
            )

    def test_sweeps_and_bar_values(self):
        record = compare_allocations(
            {
                "use_baseline_defaults": True,
                "rack_limit": 6000,
                "operating_reserve_pct": 10,
                "growth_reserve_pct": 20,
                "reserve_basis": "facility",
            }
        )
        rows = chart_data(record, "reserve_gpu")
        self.assertEqual(rows[-1]["pct"], 90)
        self.assertEqual(rows[-1]["partial_gpus"], 0)
        current = next(row for row in rows if row["pct"] == 20)
        self.assertEqual(
            current["whole_gpus"], record["allocation"]["whole_pod"]["total_gpus"]
        )
        density = chart_data(record, "rack_density")
        self.assertEqual(
            {row["constraint"] for row in density}, {"power", "rack_space"}
        )
        self.assertTrue(
            all(r["feasible_racks"] == min(6000, r["power_racks"]) for r in density)
        )
        self.assertEqual(chart_data(record, "whole_partial")[1]["total_racks"], 4968)

    def test_agent_plots_link_to_valid_result(self):
        with tempfile.TemporaryDirectory() as root:
            agent = CapacityAgent(None, output_root=Path(root))
            agent.baseline_enabled = True
            args = {
                "parameters": parameters(),
                "use_baseline_defaults": True,
                "rack_limit": 6000,
                "reserve_basis": None,
                "growth_reserve_pct": None,
                "operating_reserve_pct": None,
            }
            record = agent._invoke("compare_allocations", json.dumps(args))["data"]
            for kind in ("reserve_gpu", "rack_density", "whole_partial"):
                plot = agent._invoke(
                    "generate_capacity_plot",
                    json.dumps(
                        {"analysis_type": kind, "result_id": record["result_id"]}
                    ),
                )["data"]
                path = Path(plot["saved_png_path"])
                self.assertTrue(path.is_relative_to(Path(root)))
                self.assertEqual(
                    path.read_bytes()[:8], bytes.fromhex("89504e470d0a1a0a")
                )
                self.assertEqual(plot["source_result_id"], record["result_id"])
            self.assertFalse(
                agent._invoke(
                    "generate_capacity_plot",
                    json.dumps(
                        {"analysis_type": "rack_density", "result_id": "absent"}
                    ),
                )["ok"]
            )
