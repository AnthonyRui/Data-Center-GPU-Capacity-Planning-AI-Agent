# OpsAI integration / OpsAI 接入说明

This repository is a reusable capacity-planning module for a future OpsAI
operations application. The current integration is **local Python**, not a hosted
API or a completed Dashboard. Existing CLI entry points and model arithmetic remain.

本仓库提供可独立运行的容量计算模块。本轮交付本地调用示例与接口说明，
尚未交付运营分析、网页或自动扩容功能。

## Run without AI / 无需 AI 运行

With the existing model dependencies installed, from the repository root:

```sh
python examples/opsai_capacity.py
python examples/phase1a_tools.py --output-dir generated/integration
```

The first example shows how an application receives capacity results or validation
errors; the second exercises all four tools and saves verified PNGs. Neither needs
an API key. No separate calculation engine or new dependency is introduced.

## Application contracts / 应用接口

Import tools from `agent`. Full request examples and validation rules are in
[the tool guide](agent_tools.md). All values are finite JSON numbers; counts are
positive integers. PUE is a ratio, facility capacity is MW, server/network power
is kW. Strings, booleans and explicit nulls are not numeric inputs.

| Tool | Inputs | Returned evidence |
| --- | --- | --- |
| `calculate_capacity` | `parameters`, explicit `use_baseline_defaults` | `result`, `units`, `provenance`, `assumptions_used`, `explanation` |
| `compare_scenarios` | `scenarios`: named catalog entries or custom request objects | `rows`, `tradeoffs`, per-scenario provenance/defaults, units and explanation |
| `run_pue_sensitivity` | fixed `parameters`, `pue_start`, `pue_end`, `step`, baseline opt-in | `rows`, `range`, `summary`, provenance/defaults, units and explanation |
| `generate_capacity_plot` | `analysis_type`, unmodified calculated `result_data`, relative PNG `output_path` | verified `saved_png_path`, `metadata`, explanation |

`dispatch_tool(name, arguments)` returns `{"ok": true, "data": ...}` or
`{"ok": false, "error": ...}`. Handle errors before reading data. Error codes
include `missing_parameters` (with `missing_fields`), `invalid_parameters`,
`unknown_tool`, and `tool_unavailable`. Direct tool functions can raise exceptions;
the dispatcher is useful for UI-facing validation. A successful tool envelope is
not a certification of physical installation or equipment selection.

Baseline defaults must be a deliberate user choice. Display units, assumptions and
sources with the results. Never silently map missing server data to DGX B200.
The application must control the plot output root; keep returned calculation rows
unchanged. Plot paths are relative PNG paths, cannot escape the root, and cannot
overwrite an existing file. Serve images through a controlled application route
rather than exposing arbitrary filesystem access. The LLM's result-id plot protocol
is distinct from this trusted local Python row-based interface.

## Boundaries / 边界

Future operational analysis and this capacity module initially remain independent.
CPU high-load observations cannot directly determine GPU expansion or facility
power requirements. Scenario inputs are not operational time-series measurements.
Operating/Growth Reserve and Partial Pod are still unimplemented; their unresolved
policy does not prevent reuse of the existing whole-pod calculator.

未来 Dashboard 的运营分析与容量规划先分开展示。CPU 高负载不直接代表 GPU
扩容需求；当前 remaining capacity 是整数装填剩余，不是主动设置的安全预留。
