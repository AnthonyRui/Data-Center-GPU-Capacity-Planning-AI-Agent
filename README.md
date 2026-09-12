# GPU Rack and Pod Power Capacity Planning

**A reproducible Python model for GPU deployment under a 500 MW facility power limit.**

Convert server specifications and deployment assumptions into rack power, pod power, facility demand and whole-pod GPU capacity. Explore how PUE, rack density and pod size change the result.

**Agent extension status: Phase 1B.** A natural-language CLI now connects to the deterministic tools through an OpenAI/OpenRouter adapter. Configure your own API key and model for live use, or try a clearly labeled offline demo. Phase 1B live acceptance passed for baseline, follow-up, comparison, sensitivity, plotting and scope handling. See [acceptance evidence](docs/phase1b_acceptance.md); free-model availability can vary. See [CLI setup](docs/agent_cli.md).

**Agent 扩展进度：Phase 1B。** 已增加通过 OpenAI/OpenRouter 适配器调用确定性工具的自然语言 CLI。真实使用需配置你自己的 API Key 和模型，也可先运行明确标注的离线演示。Phase 1B 基准、追问、比较、敏感性、绘图及范围说明的真实对话验收已通过。见[验收记录](docs/phase1b_acceptance.md)，免费模型可用性仍可能波动。详见[CLI 配置说明](docs/agent_cli.md)。

![Scenario comparison](figures/readme_en/scenario_comparison.png)

The non-baseline configurations above are explicitly reconstructed assumptions. Matching rounded benchmarks does not uniquely determine the input configuration.

## Project overview

This is an independently developed personal project for data-center power analytics and GPU capacity planning. It combines a modular Python model, configurable scenarios, sensitivity analysis, automated validation and reproducible outputs.

## Engineering problem and motivation

Given a facility power budget, how many complete GPU pods can be deployed after accounting for IT power and facility overhead? Counting pods alone is insufficient: smaller pods may increase the pod count while supporting fewer GPUs. The model compares both deployment size and unused power capacity.

**Scope:** concept-level power capacity planning. This model does not certify physical rack fit, cooling feasibility or electrical construction design. MW and kW describe power, not energy consumption over time.

## Model architecture and methodology

```text
Inputs
  -> Server system
  -> Rack IT power
  -> Pod IT power
  -> Facility power
  -> Whole pods, racks, GPUs, remaining MW
```

| Quantity | Formula |
| --- | --- |
| Rack IT power (kW) | server kW × servers per rack + external network kW |
| Pod IT power (MW) | rack kW × racks per pod ÷ 1,000 |
| Pod facility power (MW) | pod IT MW × PUE |
| Maximum IT capacity (MW) | facility capacity MW ÷ PUE |
| Maximum complete pods | floor(facility capacity MW ÷ pod facility MW) |
| Total GPUs | pods × racks per pod × servers per rack × GPUs per server |
| Remaining capacity (MW) | facility capacity MW − deployed facility MW |
| Capacity utilization (%) | deployed facility MW ÷ facility capacity MW × 100 |

Intermediate calculations use unrounded values. Decimal conversion protects simple decimal floor boundaries; exported results use ordinary numeric columns. For example, using the displayed 2.25 MW instead of 2.25408 MW would incorrectly allow 222 baseline pods. Those 222 pods actually require 500.40576 MW.

## Data sources and baseline

| Input | Value | Basis |
| --- | ---: | --- |
| Facility capacity | 500 MW | Facility budget assumption |
| Server system | NVIDIA DGX B200 | Public specifications |
| Maximum server system power | 14.3 kW | NVIDIA user guide |
| GPUs per server | 8 | NVIDIA user guide |
| Servers per rack | 4 | Baseline assumption |
| External network per rack | 1.5 kW | Baseline assumption |
| Racks per pod | 32 | Baseline assumption |
| PUE | 1.20 | Scenario assumption |

NVIDIA documents eight B200 GPUs, 14.3 kW maximum system power and a 10U chassis. The model uses **whole-system power**, so it does not add individual GPU, CPU or internal network power again. The additional network term represents external rack networking. [NVIDIA DGX B200 User Guide](https://docs.nvidia.com/dgx/dgxb200-user-guide/introduction-to-dgxb200.html).

PUE values are scenario assumptions, not measurements of an operating facility. Detailed provenance and qualifications are in [model assumptions](docs/model_assumptions.md).

## Baseline results

| Metric | Result |
| --- | ---: |
| Rack IT | 58.7 kW |
| Pod IT | 1.8784 MW |
| Facility per pod | 2.25408 MW |
| Maximum IT capacity | 416.6667 MW |
| Whole pods | 221 |
| Racks | 7,072 |
| GPUs | 226,304 |
| Used facility power | 498.15168 MW |
| Remaining capacity | 1.84832 MW |
| Capacity utilization | 99.630336% |

These are power-budget upper bounds under full-pod deployment. The high utilization is a mathematical packing result, not a recommended operating target or reliability reserve.

## Scenario analysis

| Scenario | Servers/rack | Network kW/rack | Racks/pod | PUE | Input status |
| --- | ---: | ---: | ---: | ---: | --- |
| Conservative | 3 | 1.2 | 24 | 1.25 | Reconstructed |
| Baseline | 4 | 1.5 | 32 | 1.20 | Baseline configuration |
| High-Density | 5 | 2.0 | 32 | 1.15 | Reconstructed |

| Scenario | Facility MW/pod | Pods | GPUs | Remaining MW |
| --- | ---: | ---: | ---: | ---: |
| Conservative | 1.32300 | 377 | 217,152 | 1.22900 |
| Baseline | 2.25408 | 221 | 226,304 | 1.84832 |
| High-Density | 2.70480 | 184 | 235,520 | 2.31680 |

The non-baseline configurations are illustrative design assumptions selected to match rounded scenario benchmarks. They are not measured deployment data or uniquely determined configurations. Benchmarks remain in [reference data](data/original_scenario_references.csv), and [comparison results](results/reference_comparison.csv) check agreement at the benchmark display precision. Non-baseline GPU totals are calculated outputs. Multiple inputs vary between scenarios, so differences cannot be attributed to density alone.

The five-server case requires 50U for DGX B200 chassis alone, before external networking. It is a power-only illustration and must not be interpreted as a validated conventional rack layout.

## Sensitivity analysis

Each sweep changes one input around the baseline, holding all others fixed. Configure the ranges in [sensitivity_parameters.json](data/sensitivity_parameters.json).

- **PUE: 1.10–1.60, step 0.01.** Lower PUE increases the continuous IT budget; whole-pod GPU capacity changes in steps.
- **Servers per rack: 1–6.** A fixed network term is shared across more servers. Benefits depend on that assumption and integer packing; higher counts require separate physical validation.
- **Racks per pod: 8–64, step 8.** Larger deployment blocks can strand more power, but the remainder need not increase monotonically.

![PUE and GPU capacity](figures/readme_en/gpu_capacity_vs_pue.png)

## Visualizations and output files

Nine analysis figures cover power breakdown, deployment capacity, scenario comparisons and sensitivity. Two additional English variants in `figures/readme_en/` are embedded in this README. See the [figure guide](docs/figures.md). CSVs contain full model outputs and explicit units in column names; see the [data dictionary](docs/data_dictionary.md).

## Repository structure

```text
Data-Center-GPU-Power-Capacity-Planning/
├── README.md
├── requirements.txt
├── requirements-lock.txt
├── requirements-agent-lock.txt # Model + agent dependencies / 模型及 Agent 依赖
├── run_agent.py            # Interactive CLI / 交互式 CLI
├── .env.example            # Credential placeholders / 凭据占位符
├── run_analysis.py
├── src/                  # Calculations and charts
├── agent/                # Deterministic tools and validation / 确定性工具与校验
├── examples/             # Runnable tool examples / 可运行工具示例
├── data/                 # Editable inputs and references
├── results/              # Generated CSVs
├── figures/              # Generated PNGs
├── notebooks/            # Three executed notebooks
├── docs/                 # Assumptions and guides
├── scripts/              # Notebook verification
├── tests/                # Numerical and input checks
└── .github/workflows/    # Automated validation
```

## How to run

Use Python 3.12 (tested). No GPU or CUDA installation is needed. Run commands from this repository's root. `requirements-agent-lock.txt` installs the original model dependencies plus the tested agent dependencies. The original `requirements-lock.txt` remains available for model-only use. / `requirements-agent-lock.txt` 安装原模型及已测试的 Agent 依赖；仅运行原模型仍可使用 `requirements-lock.txt`。

**Windows PowerShell**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-agent-lock.txt
.\.venv\Scripts\python.exe run_analysis.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m jupyterlab
```

**macOS / Linux**

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-agent-lock.txt
.venv/bin/python run_analysis.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m jupyterlab
```

Edit `data/scenario_parameters.csv` to change scenario assumptions. Keep one unique row named `Baseline` for the sensitivity reference. Use `--output-dir experiment` to save a separate run without overwriting the bundled figures and results. The README tables describe the shipped inputs and do not update automatically after edits.

```bash
python run_analysis.py --parameters data/scenario_parameters.csv --output-dir experiment
python scripts/verify_notebooks.py
```

Charts use Chinese fonts if installed, with English fallback; Chinese explanations remain available in Markdown and notebooks on every platform. CSV files use UTF-8 with BOM for common Windows spreadsheet readers.

## Validation

Tests cover the original baseline, exact decimal floor boundaries, insufficient facility capacity, invalid inputs, signed overload, PUE monotonicity and scenario reference agreement. Three notebooks reuse `src` functions and can be executed with `scripts/verify_notebooks.py`. GitHub Actions runs these checks and regenerates outputs when the repository is pushed. See the [local validation record](docs/validation.md).

## Limitations and future work

The model assumes constant maximum server power, fixed per-rack network power, constant PUE and identical complete pods within a scenario. It does not reserve power for growth or failure conditions, allocate a separate general-purpose IT budget, or model partial pods. Capacity utilization is not GPU compute utilization.

Detailed cooling/CFD, electrical distribution, breakers, cables, transformers, UPS topology, redundancy and time-varying workloads are outside scope. Future work may add explicit operating reserves, physical rack limits and partial-pod allocation, followed by real operational power/PUE data. Machine learning is deferred until suitable data and a defined validation task are available.

## AI-Powered Capacity Planning Agent / AI 驱动的数据中心容量规划 Agent

Phase 1A provides a tested tool layer over the original engineering functions. The original model, analysis script, data and notebooks are preserved. Tools return computed values with units, parameter sources and English/Chinese context; baseline defaults require explicit opt-in. All existing runtime dependencies are reused.

Phase 1A 在原有工程函数上提供经过测试的工具层，保留原模型、分析脚本、数据及 Notebook。工具返回计算数值、单位、参数来源和中英文说明；使用基准默认值必须显式启用。复用原有运行依赖。

| Tool / 工具 | Function / 功能 |
| --- | --- |
| `calculate_capacity` | Evaluate one deployment / 计算单个部署配置 |
| `compare_scenarios` | Compare named or custom scenarios with metric extrema / 比较命名或自定义场景，返回指标极值 |
| `run_pue_sensitivity` | Sweep PUE while keeping other inputs fixed / 固定其他输入扫描 PUE |
| `generate_capacity_plot` | Verify result rows and save one PNG / 核对结果数据并保存单张 PNG |

```text
Validated request -> Registered tool -> Existing Python model
                 -> Computed result + sources + bilingual context
校验后的请求 -> 注册工具 -> 原有 Python 模型 -> 计算结果、来源及双语说明
```

After the environment setup above, run the example and tests from the repository root:

完成上面的环境配置后，从项目根目录运行示例及测试：

```bash
python examples/phase1a_tools.py
python -m unittest discover -s tests -v
```

The example exercises all four tools and saves three charts under `generated/agent/`. Each execution uses a new subdirectory, and generated files are ignored by Git. It requires no API key. The 500 MW baseline remains **221 pods, 7,072 racks and 226,304 GPUs**, with **1.84832 MW** remaining.

示例运行四个工具，将三张图保存到 `generated/agent/` 下，每次使用新的子目录；生成文件由 Git 忽略，无需 API Key。500 MW 基准保持为 **221 个 Pod、7,072 个机架、226,304 块 GPU**，剩余 **1.84832 MW**。

Phase 1B adds interactive conversation and structured OpenAI/OpenRouter tool calling. The provider code is isolated in `agent/llm_client.py`. Tool tables carry the computed numbers; the model supplies qualitative English and Chinese explanations. Plot requests reference stored result IDs. The model never supplies arbitrary shell commands or rewrites plot data.

Phase 1B 增加交互对话及结构化 OpenAI/OpenRouter 工具调用。服务适配代码隔离在 `agent/llm_client.py` 中。工具表格展示计算数值，模型提供中英文定性解释；绘图请求引用已保存的结果 ID，不向模型开放任意 shell 执行或图表数据改写。

```powershell
.\.venv\Scripts\python.exe run_agent.py --demo baseline
.\.venv\Scripts\python.exe run_agent.py --configure
.\.venv\Scripts\python.exe run_agent.py
```

The demo is scripted and needs no API key. `--configure` creates a local `.env`, defaults to OpenRouter and `openrouter/free` (press Enter twice), then reads your OpenRouter key invisibly. Paid OpenRouter models are blocked by default. With valid credentials, try “Plan a 500 MW DGX B200 deployment using the baseline PUE.” Use `/reset` to start a new conversation or `/exit` to quit.

演示为预设流程，无需 API Key。`--configure` 创建本地 `.env`，前两项回车默认选择 OpenRouter 和 `openrouter/free`，随后隐藏读取你的 OpenRouter Key，默认禁止付费模型。配置有效凭据后，可输入“按 DGX B200 基准规划 500 MW 设施，使用基准 PUE”。用 `/reset` 开始新会话，用 `/exit` 退出。

Read the [CLI guide](docs/agent_cli.md), [tool contracts](docs/agent_tools.md), [runnable examples](examples/agent_examples.md), and [Phase 1B validation record](docs/phase1b_validation.md). Offline tests cover the tool loop and SDK protocol; they do not prove live model understanding or account access. RAG and Streamlit remain later phases.

详见 [CLI 指南](docs/agent_cli.md)、[工具契约](docs/agent_tools.md)、[运行示例](examples/agent_examples.md)及 [Phase 1B 验证记录](docs/phase1b_validation.md)。离线测试验证工具循环和 SDK 协议，不代表已验证真实模型理解能力或账号权限。RAG 和 Streamlit 仍属于后续阶段。

## Uploading to GitHub / 上传到 GitHub

Upload **the contents of this repository folder**, so this README appears at the GitHub repository root. Include `data`, `results`, `figures`, notebooks and hidden configuration files. Exclude local virtual environments and temporary files. This project has not been pushed to a remote repository automatically.

上传**本项目文件夹内的内容**，使 README 位于 GitHub 仓库根目录。包含 `agent`、`examples`、`src`、测试、数据、原有结果、图表、Notebook 及隐藏配置文件；不上传虚拟环境、`generated`、日志或真实 `.env`。本项目未自动推送到远程仓库。
