"""Independent expected values and capacity boundaries. / 独立预期值与容量边界测试。"""
import unittest
from dataclasses import replace
from src.power_model import ModelInputs, evaluate, calculate_max_pods, calculate_remaining_capacity


class PowerModelTests(unittest.TestCase):
    def test_original_baseline(self):
        r = evaluate(ModelInputs())
        expected = {"rack_it_power_kw": 58.7, "pod_it_power_mw": 1.8784,
                    "pod_facility_power_mw": 2.25408, "max_pods": 221,
                    "total_racks": 7072, "total_gpus": 226304,
                    "used_capacity_mw": 498.15168, "remaining_capacity_mw": 1.84832}
        for key, value in expected.items():
            with self.subTest(key=key):
                self.assertAlmostEqual(r[key], value, places=9)
        self.assertGreater(222 * 2.25408, 500)

    def test_exact_decimal_boundary(self):
        self.assertEqual(calculate_max_pods(0.3, 0.1), 3)
        self.assertEqual(calculate_max_pods(0.299999, 0.1), 2)
        self.assertEqual(calculate_max_pods(0, 0.1), 0)

    def test_small_facility(self):
        r = evaluate(replace(ModelInputs(), facility_capacity_mw=1))
        self.assertEqual(r["total_gpus"], 0)
        self.assertEqual(r["remaining_capacity_mw"], 1)

    def test_invalid_inputs(self):
        for key, value in [("pue", 0.99), ("server_power_kw", float("nan")),
                           ("network_power_kw", -1), ("racks_per_pod", 2.5),
                           ("servers_per_rack", True), ("facility_capacity_mw", 0),
                           ("pue", float("inf"))]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                replace(ModelInputs(), **{key: value})

    def test_capacity_invariant_and_pue_monotonicity(self):
        previous = float("inf")
        for pue in (1, 1.1, 1.2, 1.4, 1.6):
            r = evaluate(replace(ModelInputs(), pue=pue))
            self.assertGreaterEqual(r["remaining_capacity_mw"], 0)
            self.assertLess(r["remaining_capacity_mw"], r["pod_facility_power_mw"])
            self.assertLessEqual(r["total_gpus"], previous)
            previous = r["total_gpus"]

    def test_signed_overload(self):
        self.assertEqual(calculate_remaining_capacity(500, 501), -1)


if __name__ == "__main__":
    unittest.main()
