"""Real PNG generation, data integrity and output boundaries. / PNG 生成、数据完整性及输出边界。"""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from agent import (
    calculate_capacity,
    compare_scenarios,
    generate_capacity_plot,
    run_pue_sensitivity,
)
from agent.schemas import ToolValidationError


class AgentPlotTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.row = calculate_capacity({"use_baseline_defaults": True})["result"]

    def request(self, **changes):
        return {
            "analysis_type": "capacity",
            "result_data": [self.row],
            "output_path": "capacity.png",
            **changes,
        }

    def test_all_three_chart_types_generate_real_pngs(self):
        comparison = compare_scenarios(
            {"scenarios": ["Baseline", "Conservative", "High-Density"]}
        )
        pue = run_pue_sensitivity(
            {
                "pue_start": 1.1,
                "pue_end": 1.6,
                "step": 0.01,
                "use_baseline_defaults": True,
            }
        )
        for kind, rows in [
            ("capacity", [self.row]),
            ("comparison", comparison["rows"]),
            ("pue_sensitivity", pue["rows"]),
        ]:
            with self.subTest(kind=kind):
                response = generate_capacity_plot(
                    self.request(
                        analysis_type=kind,
                        result_data=rows,
                        output_path=f"nested/{kind}.png",
                    ),
                    output_root=self.root,
                )
                path = Path(response["saved_png_path"])
                self.assertTrue(path.is_relative_to(self.root))
                with Image.open(path) as image:
                    self.assertEqual(image.format, "PNG")
                    self.assertGreater(image.width, 1000)
                    image.verify()
                self.assertTrue(response["metadata"]["result_verified"])
                self.assertEqual(response["metadata"]["row_count"], len(rows))
                json.dumps(response, allow_nan=False)

    def test_zero_pods_and_more_than_three_scenarios(self):
        small = calculate_capacity(
            {"parameters": {"facility_capacity_mw": 1}, "use_baseline_defaults": True}
        )["result"]
        rows = [{**small, "scenario": f"Case {i}"} for i in range(4)]
        response = generate_capacity_plot(
            self.request(analysis_type="comparison", result_data=rows),
            output_root=self.root,
        )
        self.assertTrue(Path(response["saved_png_path"]).is_file())

    def test_existing_file_is_not_overwritten(self):
        path = self.root / "capacity.png"
        path.write_bytes(b"original")
        with self.assertRaises(ToolValidationError):
            generate_capacity_plot(self.request(), output_root=self.root)
        self.assertEqual(path.read_bytes(), b"original")

    def test_unsafe_output_paths_are_rejected(self):
        paths = [
            "../outside.png",
            "/tmp/out.png",
            "C:/out.png",
            "C:out.png",
            "\\\\server\\share\\out.png",
            "nested/../../out.png",
            "out.svg",
            "out.png:stream",
            "CON.png",
            "a\\out.png",
            "a./out.png",
            "bad\n.png",
        ]
        for path in paths:
            with self.subTest(path=path), self.assertRaises(ToolValidationError):
                generate_capacity_plot(
                    self.request(output_path=path), output_root=self.root
                )
        self.assertEqual(list(self.root.iterdir()), [])

    def test_resolved_path_escape_is_rejected(self):
        # Exercise the resolved-path gate without platform-specific symlink privileges.
        # 无需特定平台的符号链接权限，验证解析后的路径边界。
        outside = self.root.parent / "outside.png"
        with (
            patch("agent.tools.Path.resolve", side_effect=[self.root, outside]),
            self.assertRaises(ToolValidationError),
        ):
            generate_capacity_plot(self.request(), output_root=self.root)

    def test_tampered_missing_and_nonfinite_results_are_rejected(self):
        for metric, value in [
            ("total_gpus", self.row["total_gpus"] + 1),
            ("used_capacity_mw", float("nan")),
            ("max_pods", True),
        ]:
            with self.subTest(metric=metric), self.assertRaises(ToolValidationError):
                generate_capacity_plot(
                    self.request(result_data=[{**self.row, metric: value}]),
                    output_root=self.root,
                )
        incomplete = dict(self.row)
        incomplete.pop("remaining_capacity_mw")
        with self.assertRaises(ToolValidationError):
            generate_capacity_plot(
                self.request(result_data=[incomplete]), output_root=self.root
            )
        self.assertEqual(list(self.root.iterdir()), [])

    def test_invalid_plot_shapes_and_types(self):
        changes = [
            {"analysis_type": "unknown"},
            {"result_data": []},
            {"result_data": [None]},
            {"result_data": [{}]},
            {"result_data": [self.row, self.row]},
            {"analysis_type": "comparison"},
            {"output_path": None},
        ]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ToolValidationError):
                generate_capacity_plot(self.request(**change), output_root=self.root)

    def test_pue_chart_rejects_mixed_configurations_and_unsorted_rows(self):
        rows = run_pue_sensitivity(
            {
                "pue_start": 1.1,
                "pue_end": 1.2,
                "step": 0.1,
                "use_baseline_defaults": True,
            }
        )["rows"]
        cases = [
            rows[::-1],
            [rows[0], rows[0]],
            [
                rows[0],
                calculate_capacity(
                    {
                        "parameters": {"pue": 1.2, "facility_capacity_mw": 300},
                        "use_baseline_defaults": True,
                    }
                )["result"],
            ],
        ]
        for data in cases:
            with self.subTest(data=data), self.assertRaises(ToolValidationError):
                generate_capacity_plot(
                    self.request(analysis_type="pue_sensitivity", result_data=data),
                    output_root=self.root,
                )

    def test_plot_uses_verified_values_and_does_not_mutate_source(self):
        rows = run_pue_sensitivity(
            {
                "pue_start": 1.1,
                "pue_end": 1.2,
                "step": 0.1,
                "use_baseline_defaults": True,
            }
        )["rows"]
        before = copy.deepcopy(rows)
        import matplotlib.pyplot as plt
        from matplotlib.figure import Figure

        savefig = Figure.savefig
        captured = []

        def capture(fig, *args, **kwargs):
            captured.extend(list(ax.lines[0].get_ydata()) for ax in fig.axes)
            return savefig(fig, *args, **kwargs)

        with patch.object(Figure, "savefig", capture):
            generate_capacity_plot(
                self.request(analysis_type="pue_sensitivity", result_data=rows),
                output_root=self.root,
            )
        self.assertEqual(captured[2], [row["total_gpus"] for row in rows])
        self.assertEqual(rows, before)
        self.assertEqual(plt.get_fignums(), [])

    def test_english_font_fallback_retains_chinese_metadata(self):
        from src.plots import configure_style

        configure_style()
        with patch("agent.plotting.configure_style", return_value=False):
            response = generate_capacity_plot(self.request(), output_root=self.root)
        self.assertEqual(response["metadata"]["labels_language"], "en")
        self.assertTrue(response["metadata"]["caption_zh"])
        self.assertTrue(response["explanation"]["zh"])
