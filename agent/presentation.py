"""Readable CLI output sourced from tools. / 从工具结果生成可读 CLI 输出。"""

import json

from .tools import UNITS

LABELS = {
    "rack_it_power_kw": ("Rack IT power", "机架 IT 功率"),
    "pod_it_power_mw": ("Pod IT power", "Pod IT 功率"),
    "pod_facility_power_mw": ("Pod facility power", "每 Pod 设施功率"),
    "max_pods": ("Maximum whole pods", "最大完整 Pod 数"),
    "total_racks": ("Total racks", "机架总数"),
    "total_gpus": ("Total GPUs", "GPU 总数"),
    "used_capacity_mw": ("Used facility power", "已用设施功率"),
    "remaining_capacity_mw": ("Remaining power", "剩余功率"),
    "capacity_utilization_pct": ("Capacity utilization", "容量利用率"),
}
ORIGINS = {
    "user_input": "user input / 用户输入",
    "public_specification": "documented public specification / 文档中的公开规格",
    "scenario_assumption": "scenario assumption / 场景假设",
}


def format_turn(turn):
    lines = ["English", turn.english, "", "中文", turn.chinese]
    for record in turn.records:
        lines += ["", f"Tool / 工具: {record['tool']}"]
        if "result_id" in record:
            lines.append(f"Result / 结果编号: {record['result_id']}")
        if "result" in record:
            for key, (english, chinese) in LABELS.items():
                lines.append(
                    f"  {english} / {chinese}: {record['result'][key]} {UNITS[key]}"
                )
        if "rows" in record:
            rows = record["rows"]
            selected = rows if len(rows) <= 12 else rows[:6] + rows[-6:]
            lines.append(
                "  Scenario or PUE | Pods | GPUs | Remaining MW / 场景或 PUE | Pod 数 | GPU 数 | 剩余 MW"
            )
            for row in selected:
                lines.append(
                    f"  {row.get('scenario', row['pue'])} | {row['max_pods']} | {row['total_gpus']} | {row['remaining_capacity_mw']}"
                )
            if len(rows) > 12:
                lines.append(
                    "  First and last rows shown; full data available with --json. / 仅显示开头及末尾行，完整数据可用 --json 查看。"
                )
        for key in ("summary", "range", "tradeoffs", "sampling_step_source"):
            if key in record:
                lines.append(
                    f"  {key} / 工具统计: "
                    + json.dumps(record[key], ensure_ascii=False)
                )
        provenance = record.get("provenance", {})
        groups = (
            provenance if record["tool"] == "compare_scenarios" else {"": provenance}
        )
        for group, sources in groups.items():
            if not sources:
                continue
            row = next(
                (
                    item
                    for item in record.get("rows", [])
                    if item.get("scenario") == group
                ),
                None,
            )
            values = row or record.get("result") or record.get("rows", [{}])[0]
            lines.append(f"  Inputs and sources / 输入与来源 {group}:")
            for field, source in sources.items():
                value = values.get(field, "")
                mark = " [default / 默认值]" if source["used_default"] else ""
                lines.append(
                    f"    {field}: {value} {UNITS[field]} — {ORIGINS[source['origin']]}{mark}; {source['source']}"
                )
            if row and row.get("notes_en"):
                lines += ["  " + row["notes_en"], "  " + row["notes_zh"]]
        if "saved_png_path" in record:
            lines.append("  PNG: " + record["saved_png_path"])
        if "explanation" in record:
            lines += [
                "  " + record["explanation"]["en"],
                "  " + record["explanation"]["zh"],
            ]
    for error in turn.errors:
        lines.append("Notice / 提示: " + error["message"])
    return "\n".join(lines)
