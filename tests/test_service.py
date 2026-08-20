"""End-to-end persistence-wrapper tests.

``core.run`` is monkeypatched with a canned state (success) or an exception
(failure), so these exercise the full create-run-persist flow with no LLM,
no Tavily, and no network.
"""

from __future__ import annotations

import pytest

from core.schemas import Plan, Task
from db import crud, service


def _fake_state() -> dict:
    return {
        "topic": "Self Attention",
        "mode": "closed_book",
        "evidence": [],
        "plan": Plan(
            blog_title="Self Attention Explained",
            audience="developers",
            tone="neutral",
            blog_kind="explainer",
            tasks=[
                Task(id=1, title="Intro", goal="g", bullets=["a", "b", "c"], target_words=200),
                Task(id=2, title="Math", goal="g", bullets=["a", "b", "c"], target_words=300),
            ],
        ),
        "sections": [(1, "## Intro\ntext"), (2, "## Math\ntext")],
        "diagram_specs": [{"placeholder": "[[DIAGRAM_1]]"}],
        "final": "# Self Attention Explained\n\nsome words go here",
    }


def test_generate_and_save_success(db, monkeypatch):
    state = _fake_state()
    monkeypatch.setattr(service, "run", lambda topic, **kw: state)

    gen = service.generate_and_save("Self Attention")

    assert gen.status == "completed"
    # no provider/model passed -> records the Groq default selection
    assert gen.llm_provider == "groq"
    assert gen.llm_model == "openai/gpt-oss-20b"
    assert gen.blog_title == "Self Attention Explained"
    assert gen.blog_kind == "explainer"
    assert gen.mode == "closed_book"
    assert gen.section_count == 2
    assert gen.diagram_count == 1
    assert gen.word_count == len(state["final"].split())
    assert gen.final_markdown.startswith("# Self Attention Explained")
    assert gen.plan_json["blog_title"] == "Self Attention Explained"
    assert gen.evidence_json == []
    assert gen.error_message is None
    assert gen.completed_at is not None
    assert gen.duration_seconds is not None and gen.duration_seconds >= 0

    # persisted, not just returned
    assert crud.get_generation(gen.id).status == "completed"


def test_generate_and_save_forwards_progress(db, monkeypatch):
    calls = []

    def fake_run(topic, *, provider=None, model=None, on_progress=None, output_path=None):
        if on_progress:
            on_progress("router", "Routing")
        return _fake_state()

    monkeypatch.setattr(service, "run", fake_run)
    service.generate_and_save("T", on_progress=lambda n, l: calls.append((n, l)))
    assert ("router", "Routing") in calls


def test_generate_and_save_captures_failure(db, monkeypatch):
    def boom(topic, **kw):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(service, "run", boom)

    gen = service.generate_and_save("Broken Topic")
    assert gen.status == "failed"
    assert "kaboom" in gen.error_message
    assert gen.completed_at is not None
    assert crud.get_generation(gen.id).status == "failed"


def test_generate_and_save_raise_on_error(db, monkeypatch):
    def boom(topic, **kw):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(service, "run", boom)

    with pytest.raises(RuntimeError):
        service.generate_and_save("Broken Topic", raise_on_error=True)

    # failure still persisted before re-raising
    rows = crud.list_generations()
    assert len(rows) == 1
    assert rows[0].status == "failed"
    assert "kaboom" in rows[0].error_message
