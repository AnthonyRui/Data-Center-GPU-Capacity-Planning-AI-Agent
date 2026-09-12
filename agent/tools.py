"""Registered wrappers around the existing model. / 现有模型的注册工具封装。"""

import json
from dataclasses import asdict
from decimal import DecimalException
from itertools import pairwise
from pathlib import Path
from types import MappingProxyType
from typing import Any

import pandas as pd

from src.power_model import ModelInputs, evaluate
from src.scenarios import load_scenarios
from src.sensitivity import sweep

from .schemas import (
    PARAMETERS,
    CapacityRequest,
    CapacityResult,
    ComparisonRequest,
    MissingParametersError,
    PlotRequest,
    PueSensitivityRequest,
    ToolValidationError,
    label,
    number,
    parse_request,
    validate_parameters,
)

ROOT = Path(__file__).resolve().parents[1]
SCENARIO_PATH = ROOT / "data/scenario_parameters.csv"
UNITS = {
    "facility_capacity_mw": "MW",
    "server_power_kw": "kW/server",
    "gpus_per_server": "GPU/server",
    "servers_per_rack": "server/rack",
    "network_power_kw": "kW/rack",
    "racks_per_pod": "rack/pod",
    "pue": "ratio",
    "rack_it_power_kw": "kW/rack",
    "pod_it_power_mw": "MW/pod",
    "pod_facility_power_mw": "MW/pod",
    "max_it_capacity_mw": "MW",
    "max_pods": "pod",
    "total_racks": "rack",
    "total_gpus": "GPU",
    "deployed_it_power_mw": "MW",
    "used_capacity_mw": "MW",
    "remaining_capacity_mw": "MW",
    "capacity_utilization_pct": "%",
    "deployed_overhead_mw": "MW",
}
SCOPE = {
    "en": "Concept-level power capacity estimate for complete pods. Physical rack fit, cooling, "
    "reserves and electrical equipment sizing are outside this model. Remaining power is "
    "an integer-packing remainder, not an operating reserve.",
    "zh": "完整 Pod 的概念级功率容量估算。模型不验证机架物理安装、冷却、预留余量或电气设备选型。"
    "剩余功率来自整数装填约束，不是运行安全预留。",
}


def _catalog():
    return {
        row["scenario"]: (row, inputs) for row, inputs in load_scenarios(SCENARIO_PATH)
    }


def _source(name, value, used_default=False):
    # Public specifications are the values already documented in this project.
    # 公开规格仅指本项目已有文档中的值，不将编辑后的任意 CSV 值标为公开规格。
    public = name in {"server_power_kw", "gpus_per_server"} and value == getattr(
        ModelInputs(), name
    )
    return {
        "origin": "public_specification" if public else "scenario_assumption",
        "used_default": used_default,
        "source": "docs/model_assumptions.md"
        if public
        else "data/scenario_parameters.csv",
    }


def _resolve(request: CapacityRequest, catalog=None):
    supplied = validate_parameters(request.parameters)
    missing = [name for name in PARAMETERS if name not in supplied]
    if missing and not request.use_baseline_defaults:
        raise MissingParametersError(missing)
    values, provenance = dict(supplied), {}
    if missing:
        catalog = _catalog() if catalog is None else catalog
        if "Baseline" not in catalog:
            raise ToolValidationError(
                "Baseline scenario is unavailable / 基准场景不存在"
            )
        baseline = asdict(catalog["Baseline"][1])
        for name in missing:
            values[name] = baseline[name]
            provenance[name] = _source(name, values[name], used_default=True)
    for name in supplied:
        provenance[name] = {
            "origin": "user_input",
            "used_default": False,
            "source": "request.parameters",
        }
    return ModelInputs(**values), provenance, missing


def _finite_result(result):
    # Reject numerical overflow before JSON transport or plotting. / JSON 传输或绘图前拒绝数值溢出。
    try:
        json.dumps(result, allow_nan=False)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ToolValidationError(
            "Result cannot be represented as finite JSON / 结果无法表示为有限 JSON 数值"
        ) from exc
    return result


def _evaluate(inputs):
    try:
        return _finite_result(evaluate(inputs))
    except (OverflowError, DecimalException, ZeroDivisionError) as exc:
        raise ToolValidationError(
            "Inputs exceed supported numerical resolution / 输入超出支持的数值精度范围"
        ) from exc


def calculate_capacity(request: CapacityRequest | dict) -> CapacityResult:
    """Evaluate one deployment; defaults require opt-in. / 计算单个部署，默认值需要显式启用。"""
    request = parse_request(request, CapacityRequest)
    inputs, provenance, defaults = _resolve(request)
    return {
        "tool": "calculate_capacity",
        "result": _evaluate(inputs),
        "provenance": provenance,
        "assumptions_used": defaults,
        "units": dict(UNITS),
        "explanation": dict(SCOPE),
    }


def compare_scenarios(request: ComparisonRequest | dict) -> dict[str, Any]:
    """Compare named and explicit scenarios without choosing a universal winner.
    比较命名场景与自定义场景，不定义脱离指标的绝对最优方案。
    """
    request = parse_request(request, ComparisonRequest)
    catalog = _catalog()
    rows, provenance, defaults = [], {}, {}
    for item in request.scenarios:
        if isinstance(item, str):
            if item not in catalog:
                raise ToolValidationError("Unknown scenario name / 未知场景名称")
            metadata, inputs = catalog[item]
            name = item
            sources = {
                key: _source(key, value) for key, value in asdict(inputs).items()
            }
            used_defaults = []
        else:
            name = item.name
            inputs, sources, used_defaults = _resolve(
                CapacityRequest(
                    parameters=item.parameters,
                    use_baseline_defaults=item.use_baseline_defaults,
                ),
                catalog,
            )
            metadata = {
                "input_status": "user_configuration",
                "notes_en": "User configuration; any baseline defaults are listed separately.",
                "notes_zh": "用户配置；如有基准默认值，会单独列出。",
            }
        rows.append(
            {
                "scenario": name,
                **_evaluate(inputs),
                **{
                    key: metadata[key]
                    for key in ("input_status", "notes_en", "notes_zh")
                },
            }
        )
        provenance[name], defaults[name] = sources, used_defaults

    tradeoffs = {}
    for metric in (
        "total_gpus",
        "max_pods",
        "remaining_capacity_mw",
        "capacity_utilization_pct",
    ):
        low, high = min(row[metric] for row in rows), max(row[metric] for row in rows)
        tradeoffs[metric] = {
            "minimum": low,
            "maximum": high,
            "minimum_scenarios": [
                row["scenario"] for row in rows if row[metric] == low
            ],
            "maximum_scenarios": [
                row["scenario"] for row in rows if row[metric] == high
            ],
        }
    return {
        "tool": "compare_scenarios",
        "rows": rows,
        "tradeoffs": tradeoffs,
        "provenance": provenance,
        "assumptions_used": defaults,
        "units": dict(UNITS),
        "explanation": {
            "en": "Extrema include ties. More pods need not mean more GPUs. Multiple inputs may vary; "
            "these comparisons do not establish causation. Reconstructed scenarios remain illustrative. "
            + SCOPE["en"],
            "zh": "极值包含并列场景。更多 Pod 不一定意味着更多 GPU。多个输入可能同时变化，"
            "不能据此归因。重建场景仍为示例假设。" + SCOPE["zh"],
        },
    }


def run_pue_sensitivity(request: PueSensitivityRequest | dict) -> dict[str, Any]:
    """Evaluate a bounded Decimal-spaced PUE grid using the original sweep.
    使用原有 sweep 计算有数量上限的 Decimal 等步长 PUE 序列。
    """
    request = parse_request(request, PueSensitivityRequest)
    values = request.values()
    inputs, provenance, defaults = _resolve(
        CapacityRequest(
            parameters={**request.parameters, "pue": values[0]},
            use_baseline_defaults=request.use_baseline_defaults,
        )
    )
    provenance["pue"]["source"] = "request.pue_start/pue_end/step"
    _evaluate(inputs)
    try:
        rows = _finite_result(sweep(inputs, "pue", values).to_dict("records"))
    except (OverflowError, DecimalException, ZeroDivisionError) as exc:
        raise ToolValidationError(
            "Sweep exceeds supported numerical resolution / 扫描超出支持的数值精度范围"
        ) from exc
    summary = {"sample_count": len(rows)}
    for metric in ("max_it_capacity_mw", "max_pods", "total_gpus"):
        column = [row[metric] for row in rows]
        summary[metric] = {
            "minimum": min(column),
            "maximum": max(column),
            "first": column[0],
            "last": column[-1],
        }
    return {
        "tool": "run_pue_sensitivity",
        "rows": rows,
        "summary": summary,
        "range": {
            "start": request.pue_start,
            "requested_end": request.pue_end,
            "actual_end": values[-1],
            "step": request.step,
        },
        "provenance": provenance,
        "assumptions_used": defaults,
        "units": dict(UNITS),
        "explanation": {
            "en": "Only PUE varies. The end is included only when it lies on the sampling grid. "
            "Sampled steps are not exact analytical transition locations. "
            + SCOPE["en"],
            "zh": "仅改变 PUE。终点只有位于采样网格上时才包含。采样阶梯不表示解析求得的准确跳变位置。"
            + SCOPE["zh"],
        },
    }


def _plot_rows(request):
    rows = []
    for row in request.result_data:
        if any(name not in row for name in PARAMETERS):
            raise ToolValidationError(
                "Plot rows need complete model inputs / 图表数据须含完整模型输入"
            )
        inputs = ModelInputs(
            **validate_parameters({name: row[name] for name in PARAMETERS})
        )
        expected = _evaluate(inputs)
        for name, value in expected.items():
            if name not in row:
                raise ToolValidationError(
                    "Plot rows need complete calculated results / 图表数据须含完整计算结果"
                )
            number(row[name], name)
            if row[name] != value:
                raise ToolValidationError(
                    "Plot result differs from the model / 图表结果与模型计算不一致"
                )
        if request.analysis_type == "comparison":
            label(row.get("scenario"))
            expected["scenario"] = row["scenario"]
        rows.append(expected)
    if request.analysis_type == "capacity" and len(rows) != 1:
        raise ToolValidationError(
            "Capacity plot requires one row / 容量图仅接受一行结果"
        )
    if request.analysis_type == "comparison":
        names = [row["scenario"] for row in rows]
        if not 2 <= len(rows) <= 50 or len(names) != len(set(names)):
            raise ToolValidationError(
                "Comparison requires 2–50 unique scenarios / 对比图需要 2–50 个不同场景"
            )
    if request.analysis_type == "pue_sensitivity":
        if any(b["pue"] <= a["pue"] for a, b in pairwise(rows)):
            raise ToolValidationError(
                "PUE rows must be strictly increasing / PUE 行必须严格递增"
            )
        if any(
            row[name] != rows[0][name]
            for row in rows
            for name in PARAMETERS
            if name != "pue"
        ):
            raise ToolValidationError("Only PUE may vary / 只能改变 PUE")
    return rows


def generate_capacity_plot(
    request: PlotRequest | dict, *, output_root: Path | None = None
) -> dict[str, Any]:
    """Save one verified PNG below a trusted output root, never overwrite a file.
    在可信输出目录下保存一张经过数值验证的 PNG，不覆盖已有文件。
    """
    request = parse_request(request, PlotRequest)
    rows = _plot_rows(request)
    root = (
        ROOT / "generated/agent" if output_root is None else Path(output_root)
    ).resolve()
    path = (root / request.output_path).resolve()
    if not path.is_relative_to(root):
        raise ToolValidationError(
            "Output must stay inside the output directory / 输出必须位于指定目录内"
        )
    if path.exists():
        raise ToolValidationError(
            "Output already exists; choose a new filename / 输出已存在，请使用新文件名"
        )
    from .plotting import render_plot

    metadata = render_plot(request.analysis_type, pd.DataFrame(rows), path)
    return {
        "tool": "generate_capacity_plot",
        "saved_png_path": str(path),
        "metadata": {
            "analysis_type": request.analysis_type,
            "row_count": len(rows),
            "result_verified": True,
            **metadata,
        },
        "explanation": {
            "en": "Chart values were checked against the engineering model. "
            + SCOPE["en"],
            "zh": "图表数值已与工程模型核对。" + SCOPE["zh"],
        },
    }


REGISTERED_TOOLS = MappingProxyType(
    {
        "calculate_capacity": calculate_capacity,
        "compare_scenarios": compare_scenarios,
        "run_pue_sensitivity": run_pue_sensitivity,
        "generate_capacity_plot": generate_capacity_plot,
    }
)


def dispatch_tool(name: str, arguments: dict) -> dict[str, Any]:
    """Local allowlist dispatcher, without an LLM or shell. / 本地白名单分发，不接入 LLM 或 shell。"""
    if not isinstance(name, str) or name not in REGISTERED_TOOLS:
        return {
            "ok": False,
            "error": {"code": "unknown_tool", "message": "Unknown tool / 未知工具"},
        }
    if not isinstance(arguments, dict):
        return {
            "ok": False,
            "error": {
                "code": "invalid_parameters",
                "message": "Arguments must be an object / 参数必须为对象",
            },
        }
    try:
        return {"ok": True, "data": REGISTERED_TOOLS[name](arguments)}
    except MissingParametersError as exc:
        return {
            "ok": False,
            "error": {
                "code": "missing_parameters",
                "message": str(exc),
                "missing_fields": exc.missing_fields,
            },
        }
    except ToolValidationError as exc:
        return {
            "ok": False,
            "error": {"code": "invalid_parameters", "message": str(exc)},
        }
    except (ValueError, TypeError, OverflowError, DecimalException):
        return {
            "ok": False,
            "error": {
                "code": "invalid_parameters",
                "message": "Invalid tool input or data / 工具输入或数据无效",
            },
        }
    except (OSError, ImportError):
        return {
            "ok": False,
            "error": {
                "code": "tool_unavailable",
                "message": "Tool data, output or dependency unavailable / 工具数据、输出或依赖不可用",
            },
        }
