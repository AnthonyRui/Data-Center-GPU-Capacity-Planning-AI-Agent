# Phase 2A + 2B validation / Phase 2A + 2B 验证记录

Phase 2A (local retrieval) and Phase 2B (conversation integration) are implemented. This record distinguishes automated verification from real provider observations. Phase 3 is not implemented.

Phase 2A 本地检索与 Phase 2B 对话接入已实现。本记录区分自动验证与真实模型观察结果，未实施 Phase 3。

## Automated verification / 自动验证

- 94 unit tests passed: all previous 78 tests plus 16 knowledge tests. Existing API-schema tests now expect five registered tools; the four engineering schemas remain unchanged.
- Bilingual relevance cases cover PUE, hardware, rack/pod, assumptions, remaining power and unsupported sizing. Unknown topics and path-like queries return no match; invalid lengths, limits and API-key-like queries are rejected.
- Tests cover deterministic ranking, source-file existence, path escape rejection, current-turn evidence requirements, no-match abstention, invented citation rejection, secret contamination, and offline CLI operation without API settings.
- A scripted mixed flow verifies knowledge lookup plus the original 500 MW baseline calculation. Retrieval cannot replace a required engineering result or become plot data.
- Changed Python files pass Ruff formatting/lint. The standalone Chinese CLI search displays readable bilingual source panels.

- 94 项单元测试通过：原有 78 项加新增 16 项知识测试。API schema 测试更新为五个注册工具，原四个工程工具 schema 保持不变。
- 双语相关性用例覆盖 PUE、硬件、机架/Pod、假设、剩余功率及超出范围的选型。未知主题与路径形式查询返回无匹配；非法长度、条数及疑似 API Key 查询被拒绝。
- 测试覆盖确定性排序、来源文件存在性、路径越界拒绝、本轮证据要求、无匹配时不回答、伪造引用拒绝、密钥污染拦截，以及无需 API 配置的离线 CLI 检索。
- 预设混合流程验证知识检索与原 500 MW baseline 计算。检索不能替代所需工程结果或作为绘图数据。
- 修改的 Python 文件通过 Ruff 格式及静态检查；独立中文 CLI 检索展示可读的双语来源面板。

## Live OpenRouter observations / 真实 OpenRouter 验证

Using the existing local OpenRouter configuration with `openrouter/free` and paid models disabled, the following real requests completed successfully:

使用已有本地 OpenRouter 配置、`openrouter/free` 和禁用付费模型设置，以下真实请求成功完成：

| Request / 请求 | Observed result / 观察结果 |
| --- | --- |
| What is PUE? Explain it using project sources. | `search_knowledge` called, nonempty local evidence including the PUE topic, validated bilingual `kind=knowledge` response, no tool errors. / 调用知识检索，包含 PUE 主题依据，双语知识回答通过校验。 |
| Use DGX B200 baseline defaults for a 500 MW facility. Calculate deployment capacity and explain why remaining power is not a safety reserve using sources. | Both `calculate_capacity` and `search_knowledge` called. 226,304 GPUs; reserve topic retrieved, validated bilingual `kind=answer`, no tool errors. / 同时调用计算与检索，结果为 226,304 张 GPU，引用剩余功率主题，双语回答通过校验。 |

These observations do not establish semantic correctness for every question, all free models, or future service availability. Free routing may vary, be slow or rate limited. Source panels expose the retrieved evidence for review; lexical overlap does not prove that evidence answers a question. No real credentials are stored in this report or the upload copy.

上述观察不保证所有问题、所有免费模型或未来服务可用性。免费路由可能变化、较慢或限流。来源面板展示检索证据供核对；词项匹配本身不能证明资料足够回答问题。本报告与上传副本不包含真实凭据。

## Scope of changes / 修改范围

- Added `agent/knowledge.py`, `knowledge/catalog.json`, `tests/test_knowledge.py`, and the Phase 2 guide/report.
- Updated agent tool definitions, orchestration, prompts and presentation; added the offline CLI search option; updated existing tool-count tests and README/CLI guidance.
- Added an offline knowledge-search smoke command to GitHub Actions. This phase's remote CI run is pending upload; earlier Phase 1B remote CI success is not a Phase 2 result.
- No new runtime dependencies, vector service, web frontend or engineering formula changes. Existing provider configuration and Phase 1B upload folder remain available.

- 新增本地检索模块、知识目录、知识测试及 Phase 2 指南/报告。
- 更新工具定义、对话编排、提示与展示；增加离线检索 CLI，更新已有工具数量测试、README 和使用说明。
- GitHub Actions 增加离线知识检索冒烟命令；本阶段远程 CI 待上传后运行，Phase 1B 的远程通过记录不代表 Phase 2 通过。
- 无新运行依赖、向量服务、网页前端或工程公式修改；保留已有服务配置与 Phase 1B 上传文件夹。

Original `src` and `data`: all eight source/data files match the original model copy byte for byte. / 原 `src`、`data` 共八个文件与原模型副本逐字节一致。
