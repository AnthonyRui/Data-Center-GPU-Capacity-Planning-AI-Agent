"""Application integration example; no LLM, credentials or network required."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent import dispatch_tool


def capacity_panel(parameters, *, use_baseline_defaults=False):
    """Return the existing tool envelope unchanged, including errors and sources.

    A UI must obtain baseline opt-in from its user, not infer it from missing data.
    This is an in-process example, not a deployed API or Dashboard.
    """
    return dispatch_tool("calculate_capacity", {
        "parameters": parameters,
        "use_baseline_defaults": use_baseline_defaults,
    })


if __name__ == "__main__":
    print(json.dumps(capacity_panel(
        {"facility_capacity_mw": 500, "pue": 1.2},
        use_baseline_defaults=True,
    ), ensure_ascii=False, indent=2, allow_nan=False))
