"""Local bilingual lexical retrieval; no network or model arithmetic.
本地双语词项检索，不访问网络、不执行工程计算。
"""

import json
import math
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STOP = {
    "what",
    "is",
    "are",
    "the",
    "a",
    "an",
    "of",
    "for",
    "and",
    "to",
    "in",
    "how",
    "why",
    "does",
    "do",
    "explain",
    "please",
    "this",
    "that",
    "with",
}
ALIASES = {
    "pue": ("能效", "能源效率", "电能使用效率"),
    "rack": ("机架",),
    "pod": ("机群", "部署单元"),
    "reserve": ("余量", "剩余", "预留"),
    "specification": ("规格", "参数来源", "specifications"),
    "assumption": ("假设", "默认", "基准", "baseline", "defaults"),
    "cooling": ("冷却", "制冷"),
    "scope": ("断路器", "变压器", "选型", "breaker", "transformer"),
}


def tokens(text):
    text = text.lower()
    result = [w for w in re.findall(r"[a-z][a-z0-9]*", text) if w not in STOP]
    for run in re.findall(r"[\u4e00-\u9fff]+", text):
        result.extend(run[i : i + 2] for i in range(len(run) - 1))
    for term, variants in ALIASES.items():
        if any(v in text for v in variants):
            result.append(term)
    return result


def search_knowledge(query, top_k=3):
    """Search the curated catalog only; user input never becomes a file path.
    只检索固定知识目录，用户输入不作为文件路径。
    """
    if not isinstance(query, str) or not query.strip() or len(query) > 500:
        raise ValueError(
            "Query must contain 1–500 characters / 查询长度须为 1–500 字符"
        )
    if type(top_k) is not int or not 1 <= top_k <= 5:
        raise ValueError("top_k must be an integer from 1 to 5 / top_k 须为 1–5 的整数")
    if re.search(r"\bsk-[A-Za-z0-9_-]{12,}", query):
        raise ValueError("Do not include API keys in queries / 查询中请勿包含 API Key")
    catalog = json.loads((ROOT / "knowledge/catalog.json").read_text(encoding="utf-8"))
    query_terms = set(tokens(query))
    documents = [
        Counter(
            tokens(
                " ".join(
                    [
                        c["title_en"],
                        c["title_zh"],
                        c["text_en"],
                        c["text_zh"],
                        " ".join(c["keywords"]),
                    ]
                )
            )
        )
        for c in catalog
    ]
    average = sum(sum(d.values()) for d in documents) / len(documents)
    scored = []
    for chunk, terms in zip(catalog, documents):
        score = 0.0
        matched = query_terms.intersection(terms)
        for term in matched:
            df = sum(term in d for d in documents)
            idf = math.log(1 + (len(documents) - df + 0.5) / (df + 0.5))
            frequency = terms[term]
            score += (
                idf
                * frequency
                * 2.2
                / (frequency + 1.2 * (0.25 + 0.75 * sum(terms.values()) / average))
            )
        if score > 0:
            # Catalog paths are maintained by the project, never provided by a tool caller.
            source = (ROOT / chunk["source_file"]).resolve()
            if not source.is_relative_to(ROOT.resolve()) or not source.is_file():
                raise ValueError("Invalid knowledge source / 知识来源无效")
            scored.append((score, chunk))
    scored.sort(key=lambda item: (-item[0], item[1]["id"]))
    hits = [
        {k: v for k, v in chunk.items() if k != "keywords"}
        for _, chunk in scored[:top_k]
    ]
    return {
        "tool": "search_knowledge",
        "query": query.strip(),
        "hits": hits,
        "status": "found" if hits else "no_match",
        "notice_en": "Curated project summaries, not live specifications or calculated deployment results. Sources are attached by the retrieval tool.",
        "notice_zh": "项目整理的知识摘要，不代表实时规格或部署计算结果；来源由检索工具附加。",
    }
