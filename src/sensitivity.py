"""One-at-a-time sensitivity around the baseline. / 围绕基准的单因素敏感性分析。"""
from dataclasses import replace
from decimal import Decimal
import json
import pandas as pd
from .power_model import evaluate


def sweep(inputs, parameter, values):
    """Re-evaluate full model for each value. / 每个取值均重新计算完整模型。"""
    return pd.DataFrame([{"varied_parameter": parameter, **evaluate(replace(inputs, **{parameter: v}))} for v in values])


def run_sensitivity(inputs, configuration_path):
    """Use centralized ranges; stop is inclusive. / 使用集中配置范围，包含终点。"""
    settings = json.loads(configuration_path.read_text(encoding="utf-8"))
    start, stop, step = (Decimal(str(settings["pue"][k])) for k in ("start", "stop", "step"))
    if not all(v.is_finite() for v in (start, stop, step)) or step <= 0 or stop < start:
        raise ValueError("Invalid PUE range / PUE范围无效")
    count = int((stop - start) // step) + 1
    if count > 10000:
        raise ValueError("PUE sweep too large / PUE扫描范围过大")
    pue_values = [float(start + i * step) for i in range(count)]
    return {
        "pue": sweep(inputs, "pue", pue_values),
        "rack_density": sweep(inputs, "servers_per_rack", settings["servers_per_rack"]),
        "pod_size": sweep(inputs, "racks_per_pod", settings["racks_per_pod"]),
    }
