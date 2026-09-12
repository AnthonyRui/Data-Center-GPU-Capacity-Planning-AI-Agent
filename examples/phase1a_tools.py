"""Run four deterministic tools without an API key. / 无需 API Key 运行四个确定性工具。"""

import argparse
import json
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent import (
    calculate_capacity,
    compare_scenarios,
    generate_capacity_plot,
    run_pue_sensitivity,
)


def main():
    parser = argparse.ArgumentParser(
        description="Phase 1A tool examples / Phase 1A 工具示例"
    )
    parser.add_argument("--output-dir", type=Path, default=ROOT / "generated/agent")
    args = parser.parse_args()
    capacity = calculate_capacity({"use_baseline_defaults": True})
    comparison = compare_scenarios(
        {"scenarios": ["Conservative", "Baseline", "High-Density"]}
    )
    sensitivity = run_pue_sensitivity(
        {
            "pue_start": 1.1,
            "pue_end": 1.6,
            "step": 0.01,
            "use_baseline_defaults": True,
        }
    )
    run_id = uuid4().hex[:12]
    plots = [
        generate_capacity_plot(
            {
                "analysis_type": kind,
                "result_data": rows,
                "output_path": f"{run_id}/{kind}.png",
            },
            output_root=args.output_dir,
        )
        for kind, rows in [
            ("capacity", [capacity["result"]]),
            ("comparison", comparison["rows"]),
            ("pue_sensitivity", sensitivity["rows"]),
        ]
    ]
    print(
        json.dumps(
            {
                "baseline": capacity,
                "comparison": comparison,
                "pue_summary": sensitivity["summary"],
                "plots": plots,
            },
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
