"""Entry point: run the pipeline for a topic, with coarse phase-level progress.

Replaces the notebook's blocking `app.invoke()` (cell 10). Uses `graph.stream()`
in dual mode so we can report which node just ran (for a progress UI) while still
capturing the full final state.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Optional

from .graph import get_graph
from .llm import set_active_llm

# node name -> human label shown in the UI
PHASE_LABELS = {
    "router": "Routing",
    "research": "Researching",
    "orchestrator": "Planning",
    "worker": "Writing sections",
    "reducer": "Generating diagrams",
}

# canonical order for a UI to pre-render pending phases
PHASE_SEQUENCE = ["router", "research", "orchestrator", "worker", "reducer"]


def _initial_state(topic: str) -> dict:
    return {
        "topic": topic,
        "mode": "",
        "needs_research": False,
        "queries": [],
        "evidence": [],
        "plan": None,
        "sections": [],
        "merged_md": "",
        "md_with_placeholders": "",
        "diagram_specs": [],
        "final": "",
    }


def run(
    topic: str,
    *,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    on_progress: Optional[Callable[[str, str], None]] = None,
    output_path: Optional[str] = None,
) -> dict:
    """Run the full pipeline for `topic` and return the final state dict.

    Args:
        topic: the blog topic.
        provider: optional LLM provider (e.g. ``"groq"``, ``"google"``). When
            given with ``model``, becomes the active selection for every node in
            this run; otherwise the env default (Groq llama-3.3-70b) is used.
        model: optional model id paired with ``provider``.
        on_progress: optional callback ``(node_name, label)`` fired as each node
            completes. Fires multiple times for ``"worker"`` (parallel fan-out);
            de-dupe in the UI if needed.
        output_path: optional path to write the final Markdown to. When omitted,
            nothing is written to disk (persistence is the caller's concern).

    Returns:
        The final graph state (includes ``final``, ``plan``, ``evidence``, ...).
    """
    set_active_llm(provider, model)

    graph = get_graph()
    initial = _initial_state(topic)

    # Cap parallel section workers so we don't blow past provider rate limits
    # (e.g. Groq's free-tier TPM) when the orchestrator fans out many sections.
    config = {"max_concurrency": int(os.getenv("PIPELINE_MAX_CONCURRENCY", "2"))}

    final_state: Optional[dict] = None
    # "updates" -> {node_name: partial_update}; "values" -> full state snapshot.
    for mode, chunk in graph.stream(
        initial, config=config, stream_mode=["updates", "values"]
    ):
        if mode == "updates":
            if on_progress:
                for node_name in chunk:
                    on_progress(node_name, PHASE_LABELS.get(node_name, node_name))
        elif mode == "values":
            final_state = chunk

    if final_state is None:  # fallback safety — should not happen
        final_state = graph.invoke(initial, config=config)

    if output_path and final_state.get("final"):
        Path(output_path).write_text(final_state["final"], encoding="utf-8")

    return final_state
