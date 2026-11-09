"""Render allocation charts from model inputs; never accept caller-provided plot values."""

from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from uuid import uuid4

from src.allocation import allocation_plans
from src.power_model import ModelInputs


def chart_data(record, kind):
    inputs = ModelInputs(**record["inputs"])
    policy = record["reserve_inputs"]
    limit = record["allocation"]["rack_limit"]

    def solve(config=inputs, **changes):
        return allocation_plans(config, **(policy | changes), rack_limit=limit)

    if kind == "whole_partial":
        a = solve()
        return [{"policy": key, **a[key]} for key in ("whole_pod", "partial_pod")]
    if kind == "reserve_gpu":
        field = (
            "growth_reserve_pct"
            if policy["growth_reserve_pct"]
            else "operating_reserve_pct"
        )
        fixed = (
            policy["operating_reserve_pct"]
            if field == "growth_reserve_pct"
            else policy["growth_reserve_pct"]
        )
        points = sorted({*range(0, 101, 5), policy[field]})
        rows = []
        for pct in points:
            if (
                policy["reserve_basis"] == "facility"
                and Fraction(str(pct)) + Fraction(str(fixed)) > 100
            ):
                continue
            a = solve(**{field: pct})
            rows.append(
                {
                    "varied": field,
                    "pct": pct,
                    "whole_gpus": a["whole_pod"]["total_gpus"],
                    "partial_gpus": a["partial_pod"]["total_gpus"],
                }
            )
        return rows
    if kind == "rack_density":
        rows = []
        for density in sorted({*range(1, 9), inputs.servers_per_rack}):
            a = solve(replace(inputs, servers_per_rack=density))
            rows.append(
                {
                    "servers_per_rack": density,
                    "power_racks": a["power_limit_racks"],
                    "space_racks": limit,
                    "feasible_racks": a["feasible_racks"],
                    "constraint": a["limiting_constraint"],
                }
            )
        return rows
    raise ValueError("Unknown allocation chart type")


def generate_allocation_chart(record, kind, output_dir):
    """Trusted Python caller supplies destination; Agent uses its own session directory."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib.ticker import MaxNLocator

    rows = chart_data(record, kind)
    fig = Figure(figsize=(8, 4.8), layout="constrained")
    FigureCanvasAgg(fig)
    ax = fig.subplots()
    if kind == "whole_partial":
        bars = ax.bar(
            ["Whole pods only", "Whole racks allowed"],
            [r["total_gpus"] for r in rows],
            color=["#28536b", "#17856c"],
        )
        ax.bar_label(bars, fmt="{:,.0f}", padding=3)
        ax.margins(y=0.15)
        ax.set(title="GPU capacity by allocation policy", ylabel="GPUs")
    elif kind == "reserve_gpu":
        for key, label, marker in [
            ("partial_gpus", "Whole racks allowed", "o"),
            ("whole_gpus", "Whole pods only", "+"),
        ]:
            ax.plot(
                [r["pct"] for r in rows],
                [r[key] for r in rows],
                marker=marker,
                markersize=4,
                label=label,
            )
        ax.set(
            title="GPU capacity at sampled reserve levels",
            xlabel=rows[0]["varied"].replace("_pct", " (%)").replace("_", " "),
            ylabel="GPUs",
        )
        ax.legend()
    else:
        x = [r["servers_per_rack"] for r in rows]
        ax.plot(x, [r["power_racks"] for r in rows], "--", label="Power limit")
        if rows[0]["space_racks"] is not None:
            ax.axhline(
                rows[0]["space_racks"],
                color="#bd7236",
                linestyle=":",
                label="Rack positions",
            )
        ax.plot(
            x,
            [r["feasible_racks"] for r in rows],
            "o-",
            label="Feasible racks",
            alpha=0.75,
        )
        ax.set(
            title="Rack density and binding capacity limits",
            xlabel="Servers per rack",
            ylabel="Racks",
        )
        ax.legend()
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_ylim(bottom=0)
    path = Path(output_dir) / f"{kind}-{uuid4().hex}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        fig.savefig(handle, format="png", dpi=150)
    return {
        "tool": "generate_capacity_plot",
        "saved_png_path": str(path.resolve()),
        "metadata": {"analysis_type": kind, "format": "png", "row_count": len(rows)},
        "chart_data": rows,
        "explanation": {
            "en": "Computed scenarios only. Rack positions do not certify physical equipment fit.",
            "zh": "仅绘制模型计算的规划情景；机架位置数不代表已验证设备安装条件。",
        },
    }
