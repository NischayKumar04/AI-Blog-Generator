"""Persistence wrapper around the core pipeline.

``generate_and_save`` is the integration point between ``core`` (which is
deliberately database-free) and ``db``. It records a "running" row, runs the
pipeline, then writes the result — or, on failure, the error — back to that row.
The dependency direction is db -> core; ``core`` never imports ``db``.

By default a pipeline failure is *captured* (status="failed", error_message set)
and the row is returned rather than raised, so a UI can display the failure.
Pass ``raise_on_error=True`` to re-raise after the failure has been persisted.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from core import run
from core.llm import DEFAULT_SELECTION

from . import crud
from .connection import init_db
from .models import BlogGeneration

log = logging.getLogger(__name__)


def _dump(obj: Any) -> Any:
    """Return a JSON-serializable form of a pydantic model (or pass through)."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    return obj


def _extract_fields(state: dict) -> dict:
    """Map a final pipeline state onto BlogGeneration column values."""
    final = state.get("final") or ""
    evidence = state.get("evidence") or []

    fields: dict = {
        "mode": state.get("mode") or None,
        "final_markdown": final or None,
        "word_count": len(final.split()),
        "diagram_count": len(state.get("diagram_specs") or []),
        "evidence_json": [_dump(e) for e in evidence],
    }

    plan = state.get("plan")
    if plan is not None:
        fields["blog_kind"] = getattr(plan, "blog_kind", None)
        fields["blog_title"] = getattr(plan, "blog_title", None)
        fields["plan_json"] = _dump(plan)
        tasks = getattr(plan, "tasks", None)
        fields["section_count"] = len(tasks) if tasks is not None else None
    else:
        # pipeline failed before planning — fall back to whatever sections exist
        fields["section_count"] = len(state.get("sections") or []) or None

    return fields


def generate_and_save(
    topic: str,
    *,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    on_progress: Optional[Callable[[str, str], None]] = None,
    output_path: Optional[str] = None,
    ensure_schema: bool = True,
    raise_on_error: bool = False,
) -> BlogGeneration:
    """Run the pipeline for ``topic`` and persist the outcome.

    Args:
        topic: the blog topic.
        provider: optional LLM provider id; paired with ``model`` it selects the
            model for this run. Both default to ``DEFAULT_SELECTION`` (Groq
            gpt-oss-20b) and are recorded on the row for later display.
        model: optional model id paired with ``provider``.
        on_progress: optional phase-level progress callback, forwarded to ``run``.
        output_path: optional path to also write the final markdown to.
        ensure_schema: call ``init_db()`` first (idempotent). Set False if the
            caller already created the schema at startup.
        raise_on_error: if True, re-raise the pipeline exception after saving the
            failed row; if False (default), return the failed row.

    Returns:
        The persisted ``BlogGeneration`` row (status "completed" or "failed").
    """
    if ensure_schema:
        init_db()

    prov, mdl = (provider, model) if (provider and model) else DEFAULT_SELECTION

    gen = crud.create_generation(topic, status="running")
    crud.update_generation(gen.id, llm_provider=prov, llm_model=mdl)
    start = time.perf_counter()

    try:
        state = run(
            topic,
            provider=prov,
            model=mdl,
            on_progress=on_progress,
            output_path=output_path,
        )
    except Exception as exc:  # persist the failure, then optionally re-raise
        log.exception("Generation failed for topic %r", topic)
        failed = crud.update_generation(
            gen.id,
            status="failed",
            error_message=str(exc),
            completed_at=datetime.now(timezone.utc),
            duration_seconds=time.perf_counter() - start,
        )
        if raise_on_error:
            raise
        return failed

    fields = _extract_fields(state)
    fields.update(
        status="completed",
        completed_at=datetime.now(timezone.utc),
        duration_seconds=time.perf_counter() - start,
    )
    return crud.update_generation(gen.id, **fields)
