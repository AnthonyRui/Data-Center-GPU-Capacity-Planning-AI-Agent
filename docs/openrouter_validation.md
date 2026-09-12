# OpenRouter integration / OpenRouter 接入

The Phase 1B CLI now supports OpenRouter through its Responses endpoint. New interactive setup defaults to `openrouter/free`; existing OpenAI configurations remain supported. The four deterministic tools and engineering calculations are unchanged.

Phase 1B CLI 已支持 OpenRouter Responses 接口。首次交互配置默认使用 `openrouter/free`，已有 OpenAI 配置仍可使用。四个确定性工具和工程计算保持不变。

Current status: [Phase 1B live acceptance passed](phase1b_acceptance.md). The initial offline results and subsequent compatibility corrections below describe the integration history.

当前状态：[Phase 1B 真实验收已通过](phase1b_acceptance.md)。下方记录首次离线验证及后续兼容修复的历史。

## Initial validation / 首次验证

- All 78 offline unit tests passed, including three new provider tests and updated CLI setup coverage.
- Real OpenAI SDK serialization with local mock HTTP transport verified the OpenRouter endpoint, authentication header, free routing constraints, four tool definitions, structured final output and calculation result roundtrip.
- Baseline remains 221 pods and 226,304 GPUs. Existing regression tests for scenarios and PUE sensitivity passed. All eight original `src` and `data` files matched the original copy byte for byte.
- No live API request was made and no local credential file was created. Account access, free model availability and interpretation of real questions still require live verification.

- 全部 78 项离线单元测试通过，包括新增的三项服务适配测试和更新后的 CLI 配置测试。
- 使用真实 OpenAI SDK 与本地模拟 HTTP 传输，验证 OpenRouter 地址、鉴权请求头、免费路由限制、四个工具定义、结构化最终输出及计算结果往返。
- baseline 保持 221 个 Pod、226,304 张 GPU；已有场景及 PUE 敏感性回归测试通过。原 `src`、`data` 共八个文件与原始副本逐字节一致。
- 未发送真实 API 请求，未创建本地密钥文件。账号权限、免费模型可用性及真实问题理解能力仍待联网验证。

## Local acceptance / 本地验收

Run `python run_agent.py --configure`; press Enter for provider and model, then enter your OpenRouter key at the hidden prompt. Run `python run_agent.py --check-config`, followed by `python run_agent.py`. Ask for the documented baseline, then change facility capacity in a follow-up. Try comparison and sensitivity/plot prompts from [examples](../examples/agent_examples.md). Inspect interpreted parameters and tool results.

运行 `python run_agent.py --configure`，服务和模型两项直接回车，在隐藏提示处输入 OpenRouter Key。运行 `python run_agent.py --check-config`，再运行 `python run_agent.py`。先询问文档基准，再追问修改设施容量，随后尝试[示例](../examples/agent_examples.md)中的比较及敏感性绘图问题，核对识别参数和工具结果。Windows 已有 `.venv` 时用 `.\.venv\Scripts\python.exe` 代替 `python`。

The default rejects paid model IDs and sends zero input/output token price caps. Rate limits or unavailable compatible free providers cause a reported error; the application does not switch to paid models. Local configuration checking does not prove remote access. Keep `.env` out of GitHub; `.gitignore` already excludes it.

默认拒绝付费模型 ID，并发送输入/输出 token 零价格上限。限流或无兼容免费服务时显示错误，程序不会切换至付费模型。本地配置检查不代表远程访问已成功。不要将 `.env` 上传 GitHub，现有 `.gitignore` 已排除该文件。

References / 参考：[free router](https://openrouter.ai/openrouter/free), [provider routing](https://openrouter.ai/docs/guides/routing/provider-selection), [Responses endpoint](https://openrouter.ai/docs/api/api-reference/responses/create-responses).

## Routing correction / 路由修复

A live request reproduced HTTP 404: no endpoint could handle all requested parameters with `require_parameters=true`. Removing this overly strict optional-parameter routing filter allowed a completed response. Zero token-price caps and local schema validation remain enabled. HTTP 404 now has a specific safe diagnostic instead of a generic rejection message. The 78 offline tests still pass.

真实请求复现 HTTP 404：启用 `require_parameters=true` 后找不到支持全部请求参数的服务。移除过严的可选参数路由筛选后，已获得完整响应。仍保留 token 零价格上限与本地 schema 校验。HTTP 404 现显示专门的安全诊断信息。78 项离线测试继续通过。这次修复后的联网检查取代上文初次接入时“未发送真实请求”的历史状态。

### Completed live baseline check / 已完成真实基准验证

After removing the simultaneous final-text schema constraint from OpenRouter tool requests, the actual CLI baseline question completed successfully (exit code zero). The provider selected `calculate_capacity`; local computation returned 221 pods, 7,072 racks, 226,304 GPUs, used facility power 498.15168 MW and remaining power 1.84832 MW, followed by validated bilingual prose. This verifies this baseline interaction, not all models or all future free-router availability. The existing local credential file was neither displayed nor changed. All 78 offline tests and lint checks passed after the correction.

移除 OpenRouter 工具请求中同时施加的最终文本 schema 限制后，真实 CLI 基准问题完整执行成功（退出码零）。服务选择了 `calculate_capacity`；本地计算返回 221 个 Pod、7,072 个机架、226,304 张 GPU、已用设施功率 498.15168 MW、剩余功率 1.84832 MW，以及通过本地验证的双语解释。这验证了本次基准交互，不代表全部模型或未来免费路由始终可用。没有显示或修改现有本地密钥文件。修复后的 78 项离线测试及静态检查全部通过。
