"""Run from the repository root: python -m examples.planning_charts."""

from pathlib import Path

from agent import compare_allocations
from agent.allocation_charts import generate_allocation_chart


def main():
    record = compare_allocations({
        "use_baseline_defaults": True, "parameters": {"facility_capacity_mw": 500},
        "operating_reserve_pct": 10, "rack_limit": 6000,
    })
    for kind in ("reserve_gpu", "whole_partial", "rack_density"):
        result = generate_allocation_chart(record, kind, Path("generated/planning"))
        print(kind, result["saved_png_path"])


if __name__ == "__main__":
    main()
