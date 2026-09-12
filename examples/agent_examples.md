# Agent examples / Agent 使用示例

Install `requirements-agent-lock.txt` before running these commands. A real conversation requires your local API key and a supported model, configured with `python run_agent.py --configure`. The offline demos use scripted model responses and real engineering tools.

执行前安装 `requirements-agent-lock.txt`。真实对话需要本地 API Key 及受支持的模型，通过 `python run_agent.py --configure` 配置。离线演示使用预设模型响应和真实工程工具。

## Baseline / 基准

```powershell
.\.venv\Scripts\python.exe run_agent.py --demo baseline
```

Live prompt: “Plan a 500 MW DGX B200 deployment using the baseline PUE.”

真实提问：“按 DGX B200 基准规划 500 MW 设施，使用基准 PUE。”

Expected tool values: 221 complete pods, 7,072 racks, 226,304 GPUs and 1.84832 MW remaining. The output identifies which values came from the user and which were defaulted.

预期工具结果：221 个完整 Pod、7,072 个机架、226,304 块 GPU，剩余 1.84832 MW。输出区分用户输入与采用默认值的参数。

## Custom deployment / 自定义部署

```powershell
.\.venv\Scripts\python.exe run_agent.py --demo custom
```

Live prompt: “Use the baseline server specifications with 300 MW, PUE 1.25, 4 servers per rack and 32 racks per pod.”

真实提问：“使用基准服务器规格，设施 300 MW、PUE 1.25、每机架 4 台服务器、每 Pod 32 个机架。”

Expected tool values: 127 complete pods and 1.804 MW remaining. To change assumptions in a live session, explicitly specify the new values; the conversation retains prior context until `/reset`.

预期工具结果：127 个完整 Pod，剩余 1.804 MW。在真实会话中修改假设时，请明确输入新值；上下文保留至 `/reset`。

## PUE comparison / PUE 比较

```powershell
.\.venv\Scripts\python.exe run_agent.py --demo comparison
```

Live prompt: “Using the baseline configuration, compare PUE 1.15, 1.20 and 1.30.”

真实提问：“使用基准配置，比较 PUE 1.15、1.20 和 1.30。”

| PUE | Whole pods / 完整 Pod 数 | GPUs / GPU 数 |
| --- | ---: | ---: |
| 1.15 | 231 | 236,544 |
| 1.20 | 221 | 226,304 |
| 1.30 | 204 | 208,896 |

Only PUE changes here. Comparing the named Conservative and High-Density scenarios is different because several parameters change simultaneously.

此处仅改变 PUE。比较命名的 Conservative 与 High-Density 场景有所不同，因为其中多个参数同时变化。

## Sensitivity and plot / 敏感性与绘图

```powershell
.\.venv\Scripts\python.exe run_agent.py --demo sensitivity
```

Live prompt: “Using the baseline, scan PUE from 1.10 to 1.60 with the documented step and generate a chart.”

真实提问：“使用基准配置，按文档中的步长扫描 PUE 1.10 到 1.60，并生成图表。”

The documented step is 0.01, producing 51 samples. GPU capacity ranges from 246,784 at PUE 1.10 to 169,984 at PUE 1.60. The tool returns a real PNG path under `generated/agent/`. Its source is the stored calculation result, not numerical rows written by the model. A defaulted step is marked as a scenario assumption from the sensitivity configuration.

文档步长为 0.01，共 51 个采样点。GPU 容量由 PUE 1.10 时的 246,784 降至 PUE 1.60 时的 169,984。工具返回 `generated/agent/` 下的真实 PNG 路径，来源是已保存的计算结果，不是模型生成的数据行。采用默认步长时，其来源标注为敏感性配置中的场景假设。

## Unsupported request / 超出范围的请求

```powershell
.\.venv\Scripts\python.exe run_agent.py --demo unsupported
```

Live prompt: “What breaker size and transformer should I install?”

真实提问：“应该安装多大的断路器和变压器？”

Expected behavior: explain that detailed electrical equipment sizing is outside this model. No equipment sizing calculation or invented result should appear.

预期行为：说明详细电气设备选型超出当前模型范围，不进行设备选型计算，不编造结果。

The expected numeric values above are checked by automated tool and orchestration tests. The demos are not evidence of live natural-language model accuracy. Run these prompts against your configured API to finish live acceptance testing.

以上预期数值已由自动化工具与编排测试核对。演示不能证明真实模型的自然语言理解准确性。配置 API 后，应实际运行这些问题完成真实联网验收。
