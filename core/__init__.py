"""AI Blog Generator — core pipeline package.

Public API:
    from core import run                 # run the pipeline for a topic
    from core import build_graph, get_graph
    from core import get_llm

The multi-agent LangGraph pipeline:
    router -> (research) -> orchestrator -> [parallel section workers] -> reducer
"""

from __future__ import annotations

from .graph import build_graph, get_graph
from .llm import (
    AVAILABLE_MODELS,
    DEFAULT_SELECTION,
    get_llm,
    reset_llm,
    set_active_llm,
)
from .runner import run, PHASE_LABELS, PHASE_SEQUENCE
from .schemas import (
    Task,
    Plan,
    EvidenceItem,
    RouterDecision,
    EvidencePack,
    DiagramSpec,
    GlobalDiagramPlan,
)
from .state import State

__all__ = [
    "run",
    "build_graph",
    "get_graph",
    "get_llm",
    "reset_llm",
    "set_active_llm",
    "AVAILABLE_MODELS",
    "DEFAULT_SELECTION",
    "PHASE_LABELS",
    "PHASE_SEQUENCE",
    "State",
    "Task",
    "Plan",
    "EvidenceItem",
    "RouterDecision",
    "EvidencePack",
    "DiagramSpec",
    "GlobalDiagramPlan",
]
