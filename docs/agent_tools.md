# Deterministic capacity tools / 确定性容量工具

This page documents the Phase 1A local Python tool layer. The tools themselves need no LLM or API key. For the Phase 1B natural-language CLI, see [CLI setup](agent_cli.md). Numerical results come from the existing `src` functions. Both JSON-style dictionaries and the dataclasses in `agent/schemas.py` are accepted.

本页说明 Phase 1A 本地 Python 工具层，工具本身无需 LLM 或 API Key。Phase 1B 自然语言 CLI 见 [CLI 配置](agent_cli.md)。数值结果来自已有 `src` 函数。工具接受 JSON 风格字典，也接受 `agent/schemas.py` 中的 dataclass。

## Architecture / 架构

```text
Python caller / Python 调用方
  -> Typed request and validation / 类型化请求与校验
  -> Registered tool / 注册工具
  -> Existing deterministic model / 原有确定性模型
  -> JSON result, provenance and bilingual context / JSON 结果、来源及双语说明
```

| Tool / 工具 | Reused functions / 复用函数 | Output / 输出 |
| --- | --- | --- |
| `calculate_capacity` | `ModelInputs`, `evaluate` | Full model result, units and per-field sources / 完整模型结果、单位和逐字段来源 |
| `compare_scenarios` | `load_scenarios`, `evaluate` | CSV-ready rows, metric extrema including ties, sources / 可导出 CSV 的数据行、含并列场景的指标极值、来源 |
| `run_pue_sensitivity` | `sweep` | CSV-ready rows, requested/actual range, summary / 可导出 CSV 的数据行、请求及实际范围、统计摘要 |
| `generate_capacity_plot` | `evaluate`, `configure_style` | Verified PNG path and metadata / 经过数值核对的 PNG 路径及元数据 |

The original `generate_figures()` remains intact. The agent's separate plotting adapter follows its style and chart conventions but supports one requested chart and custom scenarios without a mandatory `Baseline` row.

原有 `generate_figures()` 保持不变。Agent 使用独立绘图适配器复用其样式和图表表达方式，支持按需生成单图和自定义场景，不要求数据中必须包含 `Baseline` 行。

## Input policy / 输入规则

`parameters` accepts only the seven existing model inputs. kW and MW are explicit in names; PUE is a dimensionless ratio. Values must be finite JSON numbers. Counts must be positive integers; strings, booleans, fractional counts and explicit `null` values are rejected. Facility/server power must be positive, external network power nonnegative, and PUE at least 1.

`parameters` 仅接受原有七个模型参数，名称明确标注 kW 与 MW，PUE 为无量纲比值。数值必须有限；数量必须为正整数。拒绝字符串、布尔值、非整数数量及显式 `null`。设施及服务器功率必须大于零，外部网络功率不能为负，PUE 不能小于 1。

Missing fields raise `MissingParametersError` unless the caller sets `use_baseline_defaults=True`. Opt-in means the caller has selected the project's baseline context; it is not automatic permission to apply DGX B200 specifications to an unknown server. Defaults are loaded from the current `Baseline` CSV row. Explicit values always win. The tools never infer equipment specifications from a product name.

缺少字段会抛出 `MissingParametersError`，除非调用方设置 `use_baseline_defaults=True`。启用该选项表示调用方已选择项目基准上下文，不能据此将 DGX B200 规格套用到未知服务器。默认值读取当前 CSV 的 `Baseline` 行，显式输入始终优先。工具不根据产品名称推测设备规格。

`provenance` labels each field as `user_input`, `public_specification` or `scenario_assumption`, with a source location and `used_default`. Public specifications refer only to the values already documented in this project; they are not re-fetched online. `assumptions_used` lists every defaulted field, including public specification defaults. Named scenarios preserve `input_status`, `notes_en` and `notes_zh`; reconstructed cases are not relabeled as measurements.

`provenance` 将每个字段标注为用户输入、公开规格或场景假设，并记录来源和 `used_default`。公开规格仅指本项目已有文档记录的值，不进行在线检索。`assumptions_used` 列出所有使用默认值的字段，包括公开规格默认值。命名场景保留 `input_status`、`notes_en` 和 `notes_zh`，重建场景不会被改标为实测数据。

## Tool contracts / 工具契约

### calculate_capacity

```python
from agent import calculate_capacity

response = calculate_capacity({
    "parameters": {"facility_capacity_mw": 300, "pue": 1.25},
    "use_baseline_defaults": True,
})
result = response["result"]
assert result["max_pods"] == 127
assert result["remaining_capacity_mw"] == 1.804
```

With the documented baseline server and layout defaults, the custom case supports 127 complete pods and leaves 1.804 MW. Inspect `provenance` and `assumptions_used` alongside the result.

采用文档中的基准服务器和布局默认值，该自定义配置可容纳 127 个完整 Pod，剩余 1.804 MW。查看结果时应同时查看 `provenance` 与 `assumptions_used`。

### compare_scenarios

```python
from agent import compare_scenarios

named = compare_scenarios({
    "scenarios": ["Conservative", "Baseline", "High-Density"],
})
custom = compare_scenarios({
    "scenarios": [
        {"name": f"PUE {pue}", "parameters": {"pue": pue},
         "use_baseline_defaults": True}
        for pue in (1.15, 1.20, 1.30)
    ],
})
```

Accepts 2–50 uniquely named scenarios, including a mixture of existing names and custom objects. `rows` contains all model columns; `tradeoffs` reports minimum/maximum values and every tied scenario for GPUs, pods, remaining MW and capacity utilization. There is no universal best design: the highest GPU count and the highest pod count can belong to different scenarios. This model has no cost or reliability objective.

接受 2–50 个名称唯一的场景，可混合使用已有名称和自定义对象。`rows` 包含全部模型字段；`tradeoffs` 返回 GPU、Pod、剩余 MW 和容量利用率的最大值、最小值及全部并列场景。不存在脱离指标的绝对最优方案，GPU 最多与 Pod 最多可能属于不同场景；模型不包含成本或可靠性目标。

### run_pue_sensitivity

```python
from agent import run_pue_sensitivity

sensitivity = run_pue_sensitivity({
    "pue_start": 1.10, "pue_end": 1.60, "step": 0.01,
    "use_baseline_defaults": True,
})
assert sensitivity["summary"]["sample_count"] == 51
```

Provide the other six model parameters in `parameters`, or explicitly allow baseline defaults. Do not also specify `parameters.pue`. Step must be positive, end at least start, and the grid at most 10,000 points. Decimal-based grid construction avoids ordinary repeated-float addition. A non-aligned end is not appended: 1.10–1.20 with step 0.03 samples 1.10, 1.13, 1.16 and 1.19. The result records both requested and actual ends. Equal start and end produces one sample.

在 `parameters` 中提供另外六个模型参数，或显式允许基准默认值。不能重复指定 `parameters.pue`。步长必须为正，终点不小于起点，最多 10,000 个采样点。使用 Decimal 构造网格，避免反复浮点加法。未对齐的终点不会被追加：1.10–1.20、步长 0.03 对应 1.10、1.13、1.16、1.19。结果同时记录请求终点与实际终点。起点等于终点时产生一个采样点。

### generate_capacity_plot

```python
from agent import generate_capacity_plot

plot = generate_capacity_plot({
    "analysis_type": "pue_sensitivity",
    "result_data": sensitivity["rows"],
    "output_path": "pue_example.png",
})
print(plot["saved_png_path"])
```

Supported types are `capacity` (one capacity result), `comparison` (2–50 named rows), and `pue_sensitivity` (increasing PUE, other inputs fixed). Pass `[response["result"]]` for a capacity chart, or another tool's `rows`. Complete inputs and outputs are required: each row is recomputed through `evaluate()` and any differing or missing model value is rejected. This verifies mathematical consistency, not the real-world truth of the supplied inputs.

支持 `capacity`（单个容量结果）、`comparison`（2–50 个命名场景）和 `pue_sensitivity`（PUE 递增，其余参数固定）。容量图传入 `[response["result"]]`，其他图传入对应工具的 `rows`。必须包含完整输入与输出，每行都会通过 `evaluate()` 重新计算；缺失或不一致的模型数值会被拒绝。这验证数学一致性，不证明输入符合真实设施。

Paths are relative to `generated/agent/` by default. Absolute paths, traversal, unsafe Windows names and non-PNG extensions are rejected; existing files are never overwritten. A trusted Python caller may set `output_root=Path(...)`; that setting is not accepted in tool-dispatch JSON. Metadata includes the chart type, row count, metrics, DPI, verification status and English/Chinese captions. If no Chinese font is available, chart labels fall back to English while Chinese captions remain in metadata.

默认输出到 `generated/agent/` 下的相对路径。拒绝绝对路径、目录穿越、Windows 不安全名称和非 PNG 扩展名，不覆盖已有文件。可信 Python 调用方可以通过关键字参数设置 `output_root=Path(...)`，工具分发 JSON 不接受该设置。元数据包含图表类型、行数、指标、DPI、核对状态及中英文图注。缺少中文字体时图中文字回退到英文，元数据仍包含中文图注。

## Errors and dispatch / 错误与分发

Direct calls raise validation exceptions. `dispatch_tool(name, arguments)` returns `{"ok": True, "data": ...}` or `{"ok": False, "error": ...}`. Error codes are `missing_parameters`, `invalid_parameters`, `unknown_tool` and `tool_unavailable`. Error responses do not echo invalid input values. Dispatch exposes exactly four registered tools, with no shell or dynamic function lookup. No credentials or session logs are created.

直接调用会抛出校验异常。`dispatch_tool(name, arguments)` 返回成功数据或结构化错误。错误码为 `missing_parameters`、`invalid_parameters`、`unknown_tool` 和 `tool_unavailable`，错误响应不回显非法输入值。分发器只暴露四个注册工具，不提供 shell 或动态函数查找。本阶段不创建凭据或会话日志。

## Run and verify / 运行与验证

From the repository root, after installing `requirements-agent-lock.txt` for the complete current test suite in a Python 3.12 virtual environment:

在 Python 3.12 虚拟环境安装 `requirements-agent-lock.txt`（当前完整测试所需依赖）后，从项目根目录运行：

```bash
python examples/phase1a_tools.py
python -m unittest discover -s tests -v
python run_analysis.py --output-dir generated/regression
python scripts/verify_notebooks.py
```

The example runs all four tools, prints JSON and saves three charts in a unique output subdirectory. Results can be converted to a table with `pandas.DataFrame(response["rows"])`; no LLM SDK or new runtime dependency is required. The test suite uses only local data and needs no API access. See [validation](phase1a_validation.md) for the recorded checks.

示例运行全部四个工具，输出 JSON，并在唯一子目录中保存三张图。可通过 `pandas.DataFrame(response["rows"])` 转换为表格，无需 LLM SDK 或新增运行依赖。测试仅使用本地数据，不需要 API。验证记录见 [Phase 1A 验证](phase1a_validation.md)。
