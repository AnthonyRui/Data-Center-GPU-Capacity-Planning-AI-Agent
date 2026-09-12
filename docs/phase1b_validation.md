# Phase 1B validation / Phase 1B 验证记录

This is the initial implementation verification record (75 tests at that time). The later OpenRouter integration passed 78 tests and live acceptance; see [final Phase 1B acceptance](phase1b_acceptance.md). The historical local checks below are retained for traceability.

本文件记录初次实现验证（当时 75 项测试）。后续 OpenRouter 接入已通过 78 项测试及真实对话验收，当前状态见[Phase 1B 最终验收](phase1b_acceptance.md)。下方保留早期本地验证证据。

## Verified locally / 本地已验证

Environment: Windows, Python 3.12.14, original locked model dependencies, OpenAI SDK 3.13.0, python-dotenv 1.2.3 and jsonschema 4.26.0. Direct dependencies are recorded in `requirements-agent-lock.txt`. The original model lock file remains unchanged.

环境：Windows、Python 3.12.14、原模型锁定依赖、OpenAI SDK 3.13.0、python-dotenv 1.2.3 和 jsonschema 4.26.0。直接依赖记录在 `requirements-agent-lock.txt` 中，原模型锁定文件保持不变。

| Check / 检查 | Result / 结果 |
| --- | --- |
| Complete unit suite / 完整单元测试 | 75 passed: 45 existing + 30 Phase 1B / 75 项通过：原有 45 项及 Phase 1B 新增 30 项 |
| Original baseline / 原基准 | 221 pods, 7,072 racks, 226,304 GPUs, 1.84832 MW remaining / 221 个 Pod、7,072 个机架、226,304 块 GPU、剩余 1.84832 MW |
| Original analysis entry / 原分析入口 | Executed; all 5 CSVs exactly match original parsed values / 执行成功，5 份 CSV 解析后的数值与原值完全一致 |
| Notebooks / Notebook | All 3 executed successfully / 3 份均执行成功 |
| CLI demos / CLI 演示 | Baseline, custom, comparison, sensitivity/plot and unsupported flows passed / 基准、自定义、比较、敏感性及绘图、超出范围流程均通过 |
| Actual SDK with mock HTTP transport / 真实 SDK 配合模拟 HTTP 传输 | Function-call arguments, result call IDs, reasoning history and structured final response verified / 已验证函数参数、结果调用标识、推理历史和结构化最终响应 |
| Invalid inputs / 非法输入 | Malformed/duplicate JSON, null normalization, invalid PUE, unknown tools and result IDs rejected / 拒绝非法及重复 JSON、错误 PUE、未知工具或结果 ID，并验证 null 适配 |
| Default handling / 默认值处理 | Unauthorized defaults denied; explicit baseline context and sampling-step source retained / 拒绝未允许的默认值，保留明确基准上下文和采样步长来源 |
| Error behavior / 错误处理 | Timeout, connection, authentication, rate-limit, refusal and incomplete-response paths tested locally / 本地测试超时、连接、鉴权、限流、拒绝和不完整响应 |
| Output behavior / 输出行为 | Tool values displayed directly; invalid numerical model prose rejected; English/Chinese sections and provenance shown / 直接展示工具数值，拒绝非法数值正文，显示双语内容及来源 |
| Credential handling / 凭据处理 | Local setup tested in temporary directories; no echo or overwrite; fake credentials excluded from payloads and displayed errors / 临时目录测试本地配置，不回显或覆盖，模拟凭据不进入请求正文或显示错误 |
| Dependencies / 依赖 | `pip check` passed / 依赖一致性检查通过 |
| Code style / 代码样式 | New Python files formatted and lint checks passed / 新增 Python 文件已格式化，静态检查通过 |

Windows/Jupyter emitted the same event-loop and local kernel-transport warnings observed in Phase 1A. They did not prevent notebook completion. No remote GitHub Actions run is claimed; the workflow now installs agent dependencies and includes an offline CLI smoke test.

Windows/Jupyter 出现与 Phase 1A 相同的事件循环及本地内核传输提示，未妨碍 Notebook 完成。本记录不宣称已运行远程 GitHub Actions；工作流现已安装 Agent 依赖，并包含离线 CLI 冒烟测试。

## Live acceptance procedure / 真实联网验收步骤

After entering your own supported model and API key through `python run_agent.py --configure`, run the five natural-language prompts in [examples](../examples/agent_examples.md). Verify correct tool selection, extracted parameters, source labels, bilingual explanations and refusal of detailed equipment sizing. Also verify a follow-up that changes facility capacity while retaining the intended other inputs.

通过 `python run_agent.py --configure` 输入自己的受支持模型和 API Key 后，运行[示例](../examples/agent_examples.md)中的五类自然语言问题。核对工具选择、参数提取、来源标签、双语解释及对详细设备选型的范围说明，还应验证通过追问修改设施容量、保留其余预期参数的流程。

`--check-config` checks local configuration only. API account access, quota, model support and actual model interpretation cannot be established by offline tests. Quantitative prose checks are conservative syntactic guards, not a semantic proof; the user should review interpreted parameters and explanations.

`--check-config` 只检查本地配置。离线测试不能确定 API 账号访问权限、额度、模型支持情况或实际模型理解能力。数值正文检查是保守的语法防护，不是语义证明；用户仍需核对识别参数及解释。

## Files / 文件

Added / 新增：

- `agent/agent.py`: session state, tool loop, stored results and error handling / 会话状态、工具循环、结果保存与错误处理。
- `agent/llm_client.py`: configuration, provider protocol and OpenAI SDK adapter / 配置、服务协议与 OpenAI SDK 适配。
- `agent/tool_definitions.py`: strict API schemas / 严格 API 契约。
- `agent/prompts.py`: model behavior and documented baseline context / 模型行为及文档基准上下文。
- `agent/presentation.py`: readable bilingual output from tool values / 从工具数值生成可读双语输出。
- `agent/demo.py`: clearly labeled scripted offline workflows / 明确标注的预设离线流程。
- `run_agent.py`: interactive and single-question CLI, local setup and demos / 交互及单次 CLI、本地配置和演示。
- `.env.example`, `requirements-agent.txt`, `requirements-agent-lock.txt`: placeholders and separate dependencies / 占位符及独立依赖。
- `tests/test_agent_loop.py`, `tests/test_llm_client.py`, `tests/test_run_agent.py`: orchestration, SDK and CLI tests / 编排、SDK 与 CLI 测试。
- `docs/agent_cli.md`, `docs/phase1b_validation.md`, `examples/agent_examples.md`: bilingual operation, validation and examples / 双语操作、验证及示例。

Updated / 更新：`README.md`, `docs/agent_tools.md`, `.github/workflows/ci.yml`.

The Phase 1A Python contracts and engineering formulas are unchanged. RAG and Streamlit were not implemented. Local environments, credentials and generated plots remain excluded from Git.

Phase 1A Python 契约与工程公式保持不变，未实现 RAG 或 Streamlit。本地环境、凭据及生成图表继续由 Git 忽略。
