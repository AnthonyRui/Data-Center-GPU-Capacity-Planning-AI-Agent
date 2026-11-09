import json
import tempfile
import unittest
from pathlib import Path

from agent import compare_allocations, dispatch_tool
from agent.agent import CapacityAgent, TurnResult
from agent.demo import parameters
from agent.presentation import format_turn
from src.allocation import allocation_plans
from src.power_model import ModelInputs, evaluate


class AllocationTests(unittest.TestCase):
    def test_baseline_equivalence_and_partial_rack_gain(self):
        inputs = ModelInputs()
        baseline = evaluate(inputs)
        plans = allocation_plans(inputs)
        whole, partial = plans["whole_pod"], plans["partial_pod"]
        for k, old in (
            ("whole_pods", "max_pods"),
            ("total_gpus", "total_gpus"),
            ("packing_remainder_mw", "remaining_capacity_mw"),
        ):
            self.assertEqual(whole[k], baseline[old])
        self.assertEqual(partial["total_racks"], 7098)
        self.assertEqual(partial["total_gpus"], 227136)
        self.assertEqual(partial["racks_in_partial_pod"], 26)

    def test_explicit_combination_and_budget_conservation(self):
        for basis, budget in (("facility", 350), ("after_operating", 360)):
            with self.subTest(basis=basis):
                a = allocation_plans(ModelInputs(), 10, 20, basis)
                self.assertEqual(a["deployable_facility_mw"], budget)
                self.assertEqual(
                    a["operating_reserve_mw"] + a["growth_reserve_mw"] + budget, 500
                )
                for key, block in (("whole_pod", 32), ("partial_pod", 1)):
                    plan = a[key]
                    self.assertAlmostEqual(
                        plan["used_facility_mw"] + plan["packing_remainder_mw"], budget
                    )
                    self.assertLess(
                        plan["packing_remainder_mw"], block * a["rack_facility_mw"]
                    )
                    self.assertGreaterEqual(plan["packing_remainder_mw"], 0)

    def test_full_reservation_and_exact_decimal_boundary(self):
        for op, growth, basis in [
            (100, 0, None),
            (0, 100, None),
            (10, 90, "facility"),
            (10, 100, "after_operating"),
        ]:
            a = allocation_plans(ModelInputs(), op, growth, basis)
            self.assertEqual(a["partial_pod"]["total_racks"], 0)
            self.assertEqual(a["whole_pod"]["packing_remainder_mw"], 0)
        # With no network overhead and unit PUE each rack uses exactly 0.1 MW.
        for capacity, racks in [(0.0999999999, 0), (0.1, 1), (0.3, 3), (0.4, 4)]:
            inputs = ModelInputs(
                facility_capacity_mw=capacity,
                server_power_kw=100,
                servers_per_rack=1,
                network_power_kw=0,
                pue=1,
                racks_per_pod=4,
            )
            plans = allocation_plans(inputs)
            self.assertEqual(plans["partial_pod"]["total_racks"], racks)
            self.assertEqual(plans["whole_pod"]["whole_pods"], racks // 4)

    def test_invalid_reserves_and_missing_basis(self):
        for value in (True, "10", -1, 101, float("nan"), float("inf")):
            for field in ("operating_reserve_pct", "growth_reserve_pct"):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    allocation_plans(ModelInputs(), **{field: value})
        for op, growth, basis in [
            (10, 20, None),
            (60, 41, "facility"),
            (0, 0, "wrong"),
        ]:
            with self.assertRaises(ValueError):
                allocation_plans(ModelInputs(), op, growth, basis)
        self.assertFalse(dispatch_tool("compare_allocations", {"unknown": 1})["ok"])
        self.assertFalse(dispatch_tool("compare_allocations", {})["ok"])

    def test_agent_schema_defaults_sources_and_display(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = CapacityAgent(None, output_root=Path(tmp))
            args = {
                "parameters": parameters(),
                "use_baseline_defaults": True,
                "operating_reserve_pct": 10,
                "growth_reserve_pct": None,
                "reserve_basis": None,
            }
            self.assertFalse(
                agent._invoke("compare_allocations", json.dumps(args))["ok"]
            )
            agent.baseline_enabled = True
            reply = agent._invoke("compare_allocations", json.dumps(args))
            self.assertTrue(reply["ok"], reply)
            data = reply["data"]
            self.assertEqual(data["allocation"]["deployable_facility_mw"], 450)
            self.assertEqual(
                data["reserve_sources"]["growth_reserve_pct"], "not specified"
            )
            self.assertIn("450", format_turn(TurnResult("ok", "好", [data])))
            args["growth_reserve_pct"] = 20
            self.assertFalse(
                agent._invoke("compare_allocations", json.dumps(args))["ok"]
            )
            self.assertIn(
                "provenance", compare_allocations({"use_baseline_defaults": True})
            )
