"""CSV scenarios with explicit provenance. / 带有明确来源的 CSV 场景。"""
from dataclasses import fields
import pandas as pd
from .power_model import ModelInputs, evaluate


def load_scenarios(path):
    """Validate parameters without truncating fractional counts. / 验证参数，不截断非整数数量。"""
    frame = pd.read_csv(path, encoding="utf-8-sig")
    names = [f.name for f in fields(ModelInputs)]
    required = ["scenario", "input_status", "notes_en", "notes_zh", *names]
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing columns / 缺少列: {sorted(missing)}")
    if frame.empty or frame["scenario"].isna().any() or frame["scenario"].duplicated().any():
        raise ValueError("Scenarios must be nonempty and unique / 场景名称不能为空或重复")
    result = []
    for row in frame.to_dict("records"):
        values = {name: row[name] for name in names}
        for name in ("gpus_per_server", "servers_per_rack", "racks_per_pod"):
            number = float(values[name])
            if not number.is_integer():
                raise ValueError(f"{name}: integer required / 必须为整数")
            values[name] = int(number)
        result.append((row, ModelInputs(**values)))
    return result


def evaluate_scenarios(path):
    """Return computed results and provenance. / 返回计算结果和来源说明。"""
    return pd.DataFrame([{**row, **evaluate(inputs)} for row, inputs in load_scenarios(path)])


def compare_references(results, references_path):
    """Compare at original display precision, never use rounded references as model inputs.
    按原始显示精度核对，绝不把舍入后的参考结果当作模型输入。
    """
    reference = pd.read_csv(references_path)
    merged = results.merge(reference, on="scenario", suffixes=("", "_reference"))
    records = []
    precision = {"rack_it_power_kw": 1, "pod_it_power_mw": 2, "pue": 2,
                 "pod_facility_power_mw": 2, "max_pods": 0}
    for _, row in merged.iterrows():
        for metric, digits in precision.items():
            actual, ref = row[metric], row[metric + "_reference"]
            records.append({"scenario": row["scenario"], "input_status": row["input_status"],
                            "metric": metric, "calculated": actual, "reference": ref,
                            "matches_display_precision": round(actual, digits) == round(ref, digits)})
    return pd.DataFrame(records)
