"""Research node — Tavily web search + LLM synthesis into deduplicated evidence.

Extracted from Notebooks/3_Image.ipynb (cell 4).
"""

from __future__ import annotations

from typing import List

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_tavily import TavilySearch

from .llm import invoke_structured
from .schemas import EvidencePack
from .state import State


def _tavily_search(query: str, max_results: int = 5) -> List[dict]:
    """Search via Tavily and normalize results.

    Requires TAVILY_API_KEY. Note: a published date is often missing, so
    downstream code must not rely on it.
    """
    tool = TavilySearch(max_results=max_results)
    response = tool.invoke({"query": query})

    # TavilySearch.invoke returns a dict like:
    # {"query": ..., "results": [...], "images": [...], ...}
    # not a bare list — pull the actual results list out.
    if isinstance(response, dict):
        items = response.get("results") or []
    elif isinstance(response, list):
        items = response
    else:
        items = []

    normalized: List[dict] = []
    for r in items:
        if not isinstance(r, dict):
            continue
        normalized.append(
            {
                "title": r.get("title") or "",
                "url": r.get("url") or "",
                "snippet": r.get("content") or r.get("snippet") or "",
                "published_at": r.get("published_date") or r.get("published_at"),
                "source": r.get("source"),
            }
        )
    return normalized


RESEARCH_SYSTEM = """You are a research synthesizer for technical writing.

Given raw web search results, produce a deduplicated list of EvidenceItem objects.

Rules:
- Only include items with a non-empty url.
- Prefer relevant + authoritative sources (company blogs, docs, reputable outlets).
- If a published date is explicitly present in the result payload, keep it as YYYY-MM-DD.
  If missing or unclear, set published_at=null. Do NOT guess.
- Keep snippets short.
- Deduplicate by URL.
"""


def research_node(state: State) -> dict:
    queries = state.get("queries", []) or []
    max_results = 6

    raw_results: List[dict] = []
    for q in queries:
        raw_results.extend(_tavily_search(q, max_results=max_results))

    if not raw_results:
        return {"evidence": []}

    pack = invoke_structured(
        EvidencePack,
        [
            SystemMessage(content=RESEARCH_SYSTEM),
            HumanMessage(content=f"Raw results:\n{raw_results}"),
        ],
    )

    # Deduplicate by URL
    dedup = {}
    for e in pack.evidence:
        if e.url:
            dedup[e.url] = e

    return {"evidence": list(dedup.values())}
