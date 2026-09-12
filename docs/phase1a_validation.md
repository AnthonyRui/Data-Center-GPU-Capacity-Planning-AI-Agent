# Phase 1A validation / Phase 1A 验证记录

Phase 1A provides four deterministic tools and parameter validation. Validation used Windows and Python 3.12.14 with the direct dependency versions in `requirements-lock.txt`. No new runtime dependency was added. LLM integration, credentials, interactive chat, RAG and Streamlit are outside this phase.

Phase 1A 提供四个确定性工具及参数校验。验证环境为 Windows、Python 3.12.14，直接依赖采用 `requirements-lock.txt` 中的版本，未新增运行依赖。本阶段不包含 LLM 接入、凭据、交互聊天、RAG 或 Streamlit。

| Check / 检查 | Result / 结果 |
| --- | --- |
| `python -m unittest discover -s tests -v` | 45 passed: 9 existing + 36 new / 45 项通过：原有 9 项及新增 36 项 |
| Baseline wrapper vs direct `evaluate(ModelInputs())` / 基准封装与直接调用 | Exact dictionary equality for all model values / 全部模型数值字典完全相等 |
| Named scenario comparison / 命名场景比较 | All rows equal existing `evaluate_scenarios()` output / 全部数据行与原场景函数输出一致 |
| PUE 1.10–1.60, step 0.01 / PUE 扫描 | 51 rows equal existing `run_sensitivity()` output / 51 行与原敏感性函数输出一致 |
| Original `run_analysis.py` / 原分析入口 | Successful; all 5 CSVs match the original values exactly / 执行成功，5 份 CSV 与原有数值逐项完全一致 |
| `python scripts/verify_notebooks.py` | All 3 notebooks executed successfully / 3 份 Notebook 均执行成功 |
| `python examples/phase1a_tools.py` | All 4 tools executed; valid JSON and 3 PNGs / 4 个工具运行成功，返回合法 JSON 和 3 张 PNG |
| Chart verification / 图表验证 | Capacity, comparison and PUE charts inspected; bilingual labels render correctly / 已检查容量、场景比较和 PUE 图，中英文标签显示正常 |
| Output boundaries / 输出边界 | Traversal, unsafe paths, overwrites and tampered values rejected / 拒绝路径越界、不安全路径、覆盖及篡改数值 |
| Invalid tool calls / 非法工具调用 | Structured errors; no input-value echo or shell execution / 结构化错误，不回显输入值，不执行 shell |

The notebook run emitted Windows/Jupyter runtime warnings about the event-loop compatibility thread and local kernel transport; every notebook completed successfully. These warnings did not change model results. GitHub Actions is configured to install the locked dependencies and run the full test suite, original analysis and notebooks; no remote workflow run is claimed.

Notebook 执行期间出现 Windows/Jupyter 关于事件循环兼容线程及本地内核传输的运行提示；全部 Notebook 均成功完成，未影响模型结果。GitHub Actions 配置为安装锁定依赖，并运行完整测试、原分析入口及 Notebook；本记录不宣称已经在远程运行 CI。

## Baseline / 基准结果

| Metric / 指标 | Value / 数值 |
| --- | ---: |
| Rack IT power / 机架 IT 功率 | 58.7 kW |
| Pod IT power / Pod IT 功率 | 1.8784 MW |
| Pod facility power / 每 Pod 设施功率 | 2.25408 MW |
| Maximum pods / 最大完整 Pod 数 | 221 |
| Total racks / 机架总数 | 7,072 |
| Total GPUs / GPU 总数 | 226,304 |
| Used facility power / 已用设施功率 | 498.15168 MW |
| Remaining power / 剩余功率 | 1.84832 MW |
| Capacity utilization / 容量利用率 | 99.630336% |

## Changed files / 文件变更

| Files / 文件 | Change / 变更 |
| --- | --- |
| `agent/__init__.py` | Public tool imports / 工具公开接口 |
| `agent/schemas.py` | Typed requests, strict validation and error types / 类型化请求、严格校验及错误类型 |
| `agent/tools.py` | Four wrappers, sources, summaries and allowlist dispatch / 四个工具封装、来源、统计及白名单分发 |
| `agent/plotting.py` | Single-chart adapter reusing original style / 复用原有样式的单图适配器 |
| `tests/test_agent_tools.py` | Numerical equivalence, provenance and JSON checks / 数值一致性、来源与 JSON 检查 |
| `tests/test_agent_parameter_validation.py` | Invalid inputs, defaults, ranges and dispatch errors / 非法输入、默认值、范围及分发错误 |
| `tests/test_agent_plots.py` | PNG output, data integrity and output-path tests / PNG 输出、数据完整性和路径测试 |
| `examples/phase1a_tools.py` | Runnable four-tool example / 可运行的四工具示例 |
| `docs/agent_tools.md` | Bilingual API contracts and examples / 双语接口契约与示例 |
| `docs/phase1a_validation.md` | This validation record / 本验证记录 |
| `README.md` | Phase status, tool overview, execution and upload instructions / 阶段状态、工具概览、运行及上传说明 |
| `.gitignore` | Ignore generated outputs/logs; allow a future `.env.example` / 忽略生成物与日志，允许未来的 `.env.example` |
| `.github/workflows/ci.yml` | Install locked dependencies and label model/tool checks / 安装锁定依赖，标明模型及工具检查 |

The original `src/`, data, results, figures, notebooks, tests, analysis script and dependency files are unchanged. Default handling and strict JSON validation are added only at the new tool boundary. The GitHub upload root is the folder containing this README, `agent/` and `src/`; local test environments and temporary review outputs are not included.

原有 `src/`、数据、结果、图表、Notebook、测试、分析脚本和依赖文件保持不变。默认值策略与严格 JSON 校验仅增加在新工具边界。GitHub 上传根目录应为包含 README、`agent/` 和 `src/` 的文件夹，不包含本地测试环境和临时检查输出。
