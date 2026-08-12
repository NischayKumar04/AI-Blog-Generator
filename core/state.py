"""LangGraph state definition for the pipeline.

The `sections` channel uses `operator.add` so parallel workers can each append
their `(task_id, section_md)` tuple and have the results concatenated.

Note: the dead `as_of` / `recency_days` keys from the notebook's `run()` are
intentionally dropped — no node reads them in the current pipeline.
"""

from __future__ import annotations

import operator
from typing import TypedDict, List, Optional, Annotated

from .schemas import EvidenceItem, Plan


class State(TypedDict):
    topic: str

    # routing / research
    mode: str
    needs_research: bool
    queries: List[str]
    evidence: List[EvidenceItem]
    plan: Optional[Plan]

    # workers
    sections: Annotated[List[tuple[int, str]], operator.add]  # (task_id, section_md)

    # reducer / diagrams
    merged_md: str
    md_with_placeholders: str
    diagram_specs: List[dict]

    final: str
