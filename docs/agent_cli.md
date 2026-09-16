# Capacity agent CLI / 容量规划 Agent 命令行

Phase 2 adds local knowledge retrieval; see [knowledge guide](phase2_knowledge.md). Existing calculation commands are unchanged.

Phase 2 增加本地知识检索，见[知识问答指南](phase2_knowledge.md)。原计算命令保持不变。

Phase 1B adds natural-language interaction to the Phase 1A deterministic tools. The OpenAI/OpenRouter adapter selects tools through structured function calling. The Python model remains responsible for all capacity calculations; the CLI displays its numeric values, units and parameter provenance. Replies include English followed by Chinese.

Phase 1B 在 Phase 1A 确定性工具上增加自然语言交互。OpenAI/OpenRouter 适配器通过结构化函数调用选择工具，Python 模型仍负责全部容量计算，CLI 展示其数值、单位和参数来源。回答先英文、后中文。

## Setup / 配置

Use Python 3.12 and run from the project root. If the project already has a working `.venv`, reuse it. Do not recreate it on every run.

使用 Python 3.12，从项目根目录运行。项目已有可用 `.venv` 时直接复用，不需要每次重建。

```powershell
# Install or update the agent dependencies / 安装或更新 Agent 依赖
.\.venv\Scripts\python.exe -m pip install -r requirements-agent-lock.txt

# Preview without a key / 无需 Key 预览
.\.venv\Scripts\python.exe run_agent.py --demo baseline

# Configure locally; the key is entered invisibly / 本地配置，Key 隐藏输入
.\.venv\Scripts\python.exe run_agent.py --configure

# Start real interactive conversation / 启动真实交互会话
.\.venv\Scripts\python.exe run_agent.py
```

On a fresh machine with Python 3.12 installed, first run `py -3.12 -m venv .venv`. If that version is not registered with the launcher, use the absolute path to an installed Python 3.12 executable with `-m venv .venv`. A Python executable bundled with another app may not appear in `py -0p`. On macOS/Linux, use `python3.12 -m venv .venv` and `.venv/bin/python` for subsequent commands.

新机器已安装 Python 3.12 时，先运行 `py -3.12 -m venv .venv`。若启动器未登记该版本，可用已安装 Python 3.12 的绝对路径执行 `-m venv .venv`。其他应用附带的 Python 不一定出现在 `py -0p` 列表中。macOS/Linux 使用 `python3.12 -m venv .venv`，后续命令改用 `.venv/bin/python`。

`--configure` asks for a provider, model ID and hidden API key. Press Enter at the first two prompts to select `openrouter` and `openrouter/free`, then paste your OpenRouter key. Create a key in your [OpenRouter account](https://openrouter.ai/settings/keys). No OpenAI account is needed for this provider. The free router selects available models supporting the requested features; availability and rate limits still apply. Setup never overwrites an existing `.env`.

`--configure` 依次询问服务、模型 ID 和隐藏输入的 API Key。前两项直接回车即可选择 `openrouter` 和 `openrouter/free`，然后粘贴你的 OpenRouter Key。可在 [OpenRouter 账户](https://openrouter.ai/settings/keys)中创建密钥，无需 OpenAI 账户。免费路由按请求能力选择可用模型，仍受服务可用性和频率限制。配置不会覆盖已有 `.env`。

If `.env` already exists, edit it locally: set `LLM_PROVIDER=openrouter`, `LLM_MODEL=openrouter/free`, `LLM_API_KEY` to your OpenRouter key, and `LLM_ALLOW_PAID_MODELS=false`. Do not share or commit this file. Alternatively copy `.env.example` to `.env` on a fresh setup. Environment variables override the file. `LLM_API_KEY` takes precedence over the provider-specific fallback (`OPENROUTER_API_KEY` or `OPENAI_API_KEY`); credentials are never taken from the other provider.

若 `.env` 已存在，在本地编辑：设置 `LLM_PROVIDER=openrouter`、`LLM_MODEL=openrouter/free`、`LLM_API_KEY` 为你的 OpenRouter Key、`LLM_ALLOW_PAID_MODELS=false`。不要分享或提交该文件。首次配置也可复制 `.env.example` 为 `.env`。环境变量优先于文件；`LLM_API_KEY` 优先于对应服务的 `OPENROUTER_API_KEY` 或 `OPENAI_API_KEY`，不会混用另一服务的 Key。

OpenRouter defaults to free models only: `openrouter/free` or IDs ending in `:free`. Requests also cap input/output token prices at zero while using default capability routing. Optional parameter metadata does not exclude otherwise usable free endpoints; local tool-argument and final-answer validation remains strict. No paid-model fallback is configured. Only deliberately setting `LLM_ALLOW_PAID_MODELS=true` permits paid models. For legacy OpenAI use, select `openai` and supply an accessible model ID; OpenAI billing is separate from this OpenRouter setting.

OpenRouter 默认仅允许 `openrouter/free` 或以 `:free` 结尾的模型，请求同时限制输入/输出 token 价格为零，并采用默认能力路由；不因可选参数元数据筛除免费服务，本地工具参数与最终回答仍严格校验，不配置付费模型回退。只有主动设置 `LLM_ALLOW_PAID_MODELS=true` 才允许付费模型。保留原 OpenAI 用法：选择 `openai` 并填写可访问的模型 ID；OpenAI 计费不受上述 OpenRouter 开关控制。

| Setting / 配置 | Meaning / 含义 |
| --- | --- |
| `LLM_API_KEY` | Required API credential / 必需 API 凭据 |
| `LLM_MODEL` | OpenRouter default: `openrouter/free`; required for OpenAI / OpenRouter 默认免费路由，OpenAI 必填 |
| `LLM_PROVIDER` | `openrouter` or `openai`; omitted means legacy OpenAI / 支持两种服务，省略时沿用 OpenAI |
| `LLM_ALLOW_PAID_MODELS` | OpenRouter only, default `false` / 仅控制 OpenRouter，默认禁止付费模型 |
| `LLM_TIMEOUT_SECONDS` | Optional, default 45; valid range 1–120 / 可选，默认 45，范围 1–120 |
| `LLM_MAX_TOOL_ROUNDS` | Optional, default 6; valid range 1–12 / 可选，默认 6，范围 1–12 |

Check syntax and configuration locally with `python run_agent.py --check-config`. This does not contact the API and does not prove the key, quota or model access works. A live `--question` is the end-to-end verification step and sends the conversation and tool summaries to the configured provider API. `store=False` is set on each request; local history is kept in memory, not saved as a transcript.

通过 `python run_agent.py --check-config` 检查本地配置。该命令不访问 API，不能证明 Key、额度或模型权限有效。真实 `--question` 请求才是端到端验证，会将对话及工具摘要发送到配置的模型服务 API。每次请求设置 `store=False`，本地历史仅保存在内存中，不写入会话日志。

## Conversation / 对话

```text
You / 用户: 按 DGX B200 基准，规划 500 MW 设施，使用基准 PUE。
You / 用户: 设施改成 300 MW，PUE 改成 1.25，其他参数不变。
You / 用户: 使用基准配置比较 PUE 1.15、1.20 和 1.30。
You / 用户: 使用基准配置，把 PUE 从 1.10 扫描到 1.60，并画图。
You / 用户: 我应该安装多大的断路器和变压器？
```

The first question establishes the baseline context. Otherwise the agent should ask for missing specifications or permission to use baseline defaults. The host also rejects a defaults-enabled call unless baseline context has been established. Source labels identify explicit user inputs, project-documented specifications and assumptions. An explicit request not to use defaults disables them; `/baseline off` is the unambiguous control. A new server type requires its actual power and GPU specification.

首个问题建立基准上下文，否则 Agent 应询问缺少的规格或是否允许默认值。主程序也会拒绝未建立基准上下文时启用默认值的调用。来源标签区分用户输入、项目文档规格和假设。明确要求不使用默认值会禁用它们，也可用 `/baseline off` 明确控制。更换服务器型号时需要实际功率和 GPU 规格。

| Command / 命令 | Behavior / 行为 |
| --- | --- |
| `/help` | Show supported requests / 显示支持的请求 |
| `/baseline on` | Allow documented baseline defaults / 允许文档基准默认值 |
| `/baseline off` | Disable baseline defaults / 禁用基准默认值 |
| `/reset` | Clear history, result IDs and default permission / 清空历史、结果 ID 及默认值许可 |
| `/exit` | Exit / 退出 |
| Ctrl+C during a request / 请求期间 Ctrl+C | Cancel and clear the conversation / 取消并清空会话 |

Single request and full JSON output:

单次请求与完整 JSON 输出：

```powershell
.\.venv\Scripts\python.exe run_agent.py --question "Use the DGX B200 baseline for a 500 MW facility."
.\.venv\Scripts\python.exe run_agent.py --question "使用基准配置扫描 PUE 并画图" --json
```

For a range, provide the desired endpoints. If a necessary range is absent, the model should ask a clarification. Displayed sensitivity tables show the first and last rows when long; `--json` retains all rows. The API receives compact sampled rows plus tool-computed summaries, while full results remain in local session memory for plotting.

扫描范围应提供所需起止点，缺少必要范围时模型应追问。较长的敏感性表格仅展示开头及末尾行，`--json` 保留全部行。API 接收压缩后的采样行和工具计算的摘要，本地会话内存保留完整结果用于绘图。

## Offline demonstration / 离线演示

```powershell
.\.venv\Scripts\python.exe run_agent.py --demo baseline
.\.venv\Scripts\python.exe run_agent.py --demo custom
.\.venv\Scripts\python.exe run_agent.py --demo comparison
.\.venv\Scripts\python.exe run_agent.py --demo sensitivity
.\.venv\Scripts\python.exe run_agent.py --demo unsupported
```

These are explicitly scripted demonstrations with a fake model client and real Python tools. They require no key and make no API requests. They do not infer arbitrary natural-language requests and do not validate a live model's understanding. The sensitivity demo generates a real PNG.

这些是明确标注的预设演示，使用模拟模型客户端和真实 Python 工具，无需 Key，不发送 API 请求。它们不解析任意自然语言，也不验证真实模型理解能力。敏感性演示会生成真实 PNG。

## Architecture and boundaries / 架构与边界

```text
run_agent.py -> CapacityAgent -> ModelClient protocol -> OpenAI / OpenRouter Responses API
                    |
                    -> strict tool arguments -> Phase 1A tool dispatcher
                    -> result IDs -> verified plotting
                    -> tool-derived tables + English and Chinese prose
```

The provider uses strict JSON schemas with required nullable fields. The adapter removes unspecified `null` parameter fields before invoking the unchanged Phase 1A contracts. Direct Phase 1A calls still reject explicit nulls. Plot calls accept a result ID, not model-written rows or paths; the host looks up complete computed data and chooses a unique PNG filename under `generated/agent/`.

服务端使用严格 JSON 契约，所有字段必填，未指定参数可以为 null。适配器在调用未改动的 Phase 1A 契约前移除这些 null。直接调用 Phase 1A 仍拒绝显式 null。绘图调用接受结果 ID，不接受模型重写的数据行或路径；主程序读取完整计算数据，并在 `generated/agent/` 下生成唯一 PNG 文件名。

All displayed numerical tables come from registered tools. Final model prose must be bilingual and qualitative; malformed output or recognizable numerical prose is rejected and retried within the round limit. This is a guard, not proof of semantic correctness: model explanations and parameter interpretation still need user review. No shell execution, RAG, live specification retrieval, web interface or detailed electrical design is exposed.

所有显示的数值表格来自注册工具。最终模型正文必须为双语定性解释，格式错误或可识别的数值正文会被拒绝，并在轮数上限内重试。该检查不是语义正确性的证明，模型解释和参数理解仍需用户核对。不提供 shell 执行、RAG、实时规格检索、网页界面或详细电气设计。

Errors, tool counts and context size are bounded. Timeouts and service errors preserve already computed results for display. Unknown tools, repeated call IDs and malformed arguments are rejected. Session history is limited; start a new session with `/reset` when prompted. Existing generated images remain after reset.

错误处理、调用轮数和上下文大小均有边界。超时与服务错误仍会展示已计算结果。未知工具、重复调用标识和非法参数会被拒绝。会话历史有限制，出现提示时通过 `/reset` 开始新会话；已生成的图片不会因重置而删除。

## GitHub and verification / GitHub 与验证

Commit `.env.example`, source, tests and documentation. Never upload `.env`, `.venv`, logs or `generated/`; they are ignored by Git. Local `.env` is a plaintext credential file, so keep it private. No API credentials are required by CI.

提交 `.env.example`、源码、测试及文档，不上传 `.env`、`.venv`、日志或 `generated/`，这些路径已由 Git 忽略。本地 `.env` 为明文凭据文件，请妥善保管。CI 不需要 API 凭据。

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe run_analysis.py --output-dir generated/regression
.\.venv\Scripts\python.exe scripts/verify_notebooks.py
```

For the distinction between local verification and live API validation, see [Phase 1B validation](phase1b_validation.md).

本地验证与真实 API 验证的区别见 [Phase 1B 验证记录](phase1b_validation.md)。

Implementation references: [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling) and [structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs).

实现参考：[OpenAI 函数调用](https://developers.openai.com/api/docs/guides/function-calling)及[结构化输出](https://developers.openai.com/api/docs/guides/structured-outputs)。

OpenRouter references: [free router](https://openrouter.ai/openrouter/free), [Responses API](https://openrouter.ai/docs/api/api-reference/responses/create-responses), [provider routing](https://openrouter.ai/docs/guides/routing/provider-selection).

OpenRouter 参考：免费路由、Responses API 和服务路由文档见上述链接。

### OpenRouter compatibility / OpenRouter 兼容处理

OpenRouter requests use API tool calls without a simultaneous forced final-text schema: live testing found free models could skip tools when both were requested. The final JSON schema is included in instructions and validated locally, with bounded correction attempts. Tool arguments continue to use strict schemas and local validation. OpenAI retains its API-enforced text schema. Low reasoning effort and a larger output allowance reduce incomplete responses from reasoning models; free service availability still varies.

OpenRouter 请求使用 API 工具调用，不同时强制最终文本 schema：真实测试发现同时使用时免费模型可能跳过工具。最终 JSON schema 写入提示并在本地验证，格式错误时进行有次数上限的纠正。工具参数仍有严格 schema 与本地校验。OpenAI 保留 API 端强制文本 schema。较低推理强度与更大的输出预算用于减少推理模型响应截断，免费服务可用性仍会波动。
