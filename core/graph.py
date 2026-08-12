"""Build and compile the full LangGraph pipeline.

    START -> router -> (research?) -> orchestrator -> [workers] -> reducer -> END

Extracted from Notebooks/3_Image.ipynb (cell 9).
"""

from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from .orchestrator import orchestrator_node, fanout
from .reducer import build_reducer_subgraph
from .research import research_node
from .router import router_node, route_next
from .state import State
from .worker import worker_node

_compiled = None


def build_graph():
    """Construct and compile a fresh copy of the main graph."""
    g = StateGraph(State)
    g.add_node("router", router_node)
    g.add_node("research", research_node)
    g.add_node("orchestrator", orchestrator_node)
    g.add_node("worker", worker_node)
    g.add_node("reducer", build_reducer_subgraph())

    g.add_edge(START, "router")
    g.add_conditional_edges(
        "router", route_next, {"research": "research", "orchestrator": "orchestrator"}
    )
    g.add_edge("research", "orchestrator")

    g.add_conditional_edges("orchestrator", fanout, ["worker"])
    g.add_edge("worker", "reducer")
    g.add_edge("reducer", END)

    return g.compile()


def get_graph():
    """Return a process-wide cached compiled graph, building it on first use."""
    global _compiled
    if _compiled is None:
        _compiled = build_graph()
    return _compiled
