# Phase 2A and 2B / 知识检索与对话接入

Phase 2 adds one `search_knowledge` tool alongside the four existing engineering tools. It retrieves curated bilingual project summaries and supplies them to the conversational model. No vector database, embedding API, new API key or extra runtime dependency is required. This is lexical retrieval augmented generation (RAG), not live web search.

Phase 2 在原四个工程工具旁增加 `search_knowledge`，检索整理好的双语项目知识并提供给对话模型。无需向量数据库、Embedding API、新 Key 或额外运行依赖。这是基于词项检索的 RAG，不是实时网络搜索。

## Use / 使用

Run from the project directory with the existing environment. The offline search command does not read API settings or call a model:

在项目目录复用已有环境。离线检索命令不读取 API 配置、不调用模型：

```powershell
.\.venv\Scripts\python.exe run_agent.py --search-knowledge "PUE 是什么意思？"
.\.venv\Scripts\python.exe run_agent.py --search-knowledge "DGX B200 规格来源" --json
```

For real conversation, reuse your existing OpenRouter `.env`, restart the CLI, and enter questions normally. Model calls use the same account quota as before; local retrieval itself incurs no API charge.

真实对话复用原 OpenRouter `.env`，重启 CLI 后正常提问。模型请求使用原账号额度，本地检索本身不产生 API 费用。

```powershell
.\.venv\Scripts\python.exe run_agent.py
```

```text
What is PUE? Explain it using project sources.
PUE 是什么意思？请根据项目资料解释并显示来源。
DGX B200 的功率和 GPU 数量来自哪里？哪些参数是项目假设？
按 DGX B200 基准规划 500 MW 设施，并根据资料解释剩余功率为什么不是安全预留。
本地资料里有没有最新 GPU 市场价格？没有依据就说明不知道。
```

The host displays bilingual source summaries and their stable IDs, repository-relative source files, section labels, source categories and original URLs where available. These citations are attached by Python, not invented by the model. The original URL is provenance, not evidence of a fresh online lookup.

程序直接展示双语知识摘要、稳定 ID、仓库内来源文件、章节标签、来源类别及可用的原始网址。引用由 Python 附加，不由模型编造。原始网址表示资料出处，不表示刚刚联网核验。

## Retrieval / 检索实现

`knowledge/catalog.json` contains six manually curated topic chunks: PUE, hardware specifications, rack/pod concepts, assumptions, remaining capacity, and model scope/cooling context. The text is original project summary material; it does not bundle restricted standards or course slides.

`knowledge/catalog.json` 包含六个经整理的主题片段：PUE、硬件规格、机架与 Pod、规划假设、剩余容量、模型范围及冷却背景。正文是项目自行整理的摘要，不打包受限标准或课程幻灯片。

`agent/knowledge.py` uses English tokens, Chinese character bigrams and a small bilingual alias dictionary, scored with BM25. Ties are ordered by stable ID. Query length is bounded to 500 characters, and `top_k` must be an integer from 1 to 5. Zero lexical overlap returns `no_match`. Users cannot select a source path or fetch a URL. No remote document ingestion is implemented.

检索采用英文词项、中文双字切分和小型双语同义词表，使用 BM25 排序，同分按稳定 ID 排序。查询最长 500 字符，`top_k` 为 1–5 的整数；没有词项匹配时返回 `no_match`。用户不能指定来源路径或抓取网址；未实现远程文档导入。

This small lexical corpus can miss paraphrases or retrieve overlapping but insufficient background. The model must say when sources cannot answer; relevance and semantic faithfulness are not mathematically guaranteed. Review source panels. To update knowledge, edit the catalog and its cited project documentation together, then run tests; no separate index rebuild is needed.

小型词项知识库可能漏掉不同表述，也可能命中相关但不足以回答问题的背景。模型必须说明资料不足；检索相关性和解释忠实性不是数学保证，请核对来源面板。更新知识时同时修改目录及引用的项目文档并运行测试，无需重建单独索引。

## Answer boundaries / 回答边界

- `kind=knowledge` requires nonempty retrieval evidence in the current turn. With no evidence, the answer must clarify or state unsupported scope.
- `kind=answer` still requires an actual engineering-tool result. Retrieval cannot create deployment tables or act as a plot source.
- Mixed questions instruct the model to call both retrieval and calculation tools. Tool arguments and final JSON are locally validated. Model-written prose remains qualitative; documented specification numbers appear in the source panel and calculated numbers in tool tables.
- Retrieved text is reference data, not executable instructions. Citation-like URLs and markers in model prose are rejected; source metadata comes from the curated catalog.

- `kind=knowledge` 需要本轮非空检索证据，无依据时应追问或说明超出资料范围。
- `kind=answer` 仍需要实际工程工具结果；检索不能产生部署表或充当绘图数据。
- 混合问题要求模型同时检索与计算；工具参数及最终 JSON 在本地校验。模型解释仍为定性正文，文档规格数值显示在来源面板，计算数值显示在工具表。
- 检索文本仅作为参考，不能作为可执行指令。模型正文中的网址及引用标记会被拒绝，来源元数据来自经整理的目录。

For detailed breaker, transformer, cooling-equipment or construction design, scope restrictions remain unchanged. Phase 3 / Streamlit is not included.

详细断路器、变压器、冷却设备及施工设计仍超出范围。本次不包含 Phase 3 或 Streamlit。
