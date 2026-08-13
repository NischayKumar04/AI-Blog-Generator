"""Structured-output resilience tests (no network, no API keys).

Exercises ``invoke_structured``'s repair path: when a provider rejects a small
model's stringified scalar (Groq ``tool_use_failed``), we recover the raw JSON
from the error and re-validate it through Pydantic's lax coercion.
"""

from __future__ import annotations

import pytest

from core import llm as llm_mod
from core.llm import _balanced_json, message_text
from core.schemas import Plan, RouterDecision

_FAILED_GEN = (
    '<function=RouterDecision> '
    '{"mode": "closed_book", "needs_research": "false", "queries": []}'
    '</function>'
)


class _RaisingStructured:
    """Stands in for ``llm.with_structured_output(schema)``; always fails."""

    def __init__(self, err: Exception):
        self._err = err

    def invoke(self, messages):
        raise self._err


class _FakeLLM:
    def __init__(self, err: Exception):
        self._err = err

    def with_structured_output(self, schema):
        return _RaisingStructured(self._err)


def _groq_tool_use_error() -> Exception:
    err = Exception("Error code: 400 - tool_use_failed")
    err.body = {"error": {"code": "tool_use_failed", "failed_generation": _FAILED_GEN}}
    return err


def test_repairs_stringified_bool_via_body(monkeypatch):
    monkeypatch.setattr(llm_mod, "_override", _FakeLLM(_groq_tool_use_error()))
    result = llm_mod.invoke_structured(RouterDecision, [])
    assert result.needs_research is False  # "false" -> False
    assert result.mode == "closed_book"
    assert result.queries == []


def test_repairs_via_string_scrape_when_no_body(monkeypatch):
    # No `.body` attribute -> falls back to scraping str(err).
    err = Exception(
        "Error code: 400 - {'error': {'code': 'tool_use_failed', "
        f"'failed_generation': '{_FAILED_GEN}'}}}}"
    )
    monkeypatch.setattr(llm_mod, "_override", _FakeLLM(err))
    result = llm_mod.invoke_structured(RouterDecision, [])
    assert result.needs_research is False


def test_repairs_python_literals_and_short_bullets(monkeypatch):
    # A Plan the way Groq's 8b actually botched it: capital-F Python bools
    # (invalid JSON) plus a task with only 2 bullets. Both must survive.
    plan_gen = (
        '<function=Plan> {"blog_title": "T", "audience": "devs", "tone": "neutral", '
        '"blog_kind": "explainer", "constraints": [], "tasks": [{"id": 1, '
        '"title": "Intro", "goal": "g", "bullets": ["a", "b"], "target_words": 200, '
        '"requires_code": False, "requires_research": False, "tags": []}]}</function>'
    )
    err = Exception("400")
    err.body = {"error": {"code": "tool_use_failed", "failed_generation": plan_gen}}
    monkeypatch.setattr(llm_mod, "_override", _FakeLLM(err))

    plan = llm_mod.invoke_structured(Plan, [])
    assert isinstance(plan, Plan)
    assert plan.blog_title == "T"
    assert len(plan.tasks) == 1
    assert plan.tasks[0].bullets == ["a", "b"]  # 2 bullets now allowed
    assert plan.tasks[0].requires_code is False


def test_unrecoverable_error_reraises(monkeypatch):
    err = ValueError("connection reset")  # nothing to salvage
    monkeypatch.setattr(llm_mod, "_override", _FakeLLM(err))
    with pytest.raises(ValueError, match="connection reset"):
        llm_mod.invoke_structured(RouterDecision, [])


def test_happy_path_returns_directly(monkeypatch):
    expected = RouterDecision(needs_research=True, mode="hybrid", queries=["q"])

    class _OKStructured:
        def invoke(self, messages):
            return expected

    class _OKLLM:
        def with_structured_output(self, schema):
            return _OKStructured()

    monkeypatch.setattr(llm_mod, "_override", _OKLLM())
    assert llm_mod.invoke_structured(RouterDecision, []) is expected


class _Msg:
    def __init__(self, content):
        self.content = content


def test_message_text_handles_str_and_block_lists():
    # plain string (Groq, Gemini 2.5)
    assert message_text(_Msg("hello ")) == "hello "
    # list of content blocks (Gemini 3.x)
    blocks = [{"type": "text", "text": "part1 "}, {"type": "text", "text": "part2"}]
    assert message_text(_Msg(blocks)) == "part1 part2"
    # mixed / bare strings and non-text blocks are skipped gracefully
    mixed = ["a", {"text": "b"}, {"type": "image", "url": "x"}]
    assert message_text(_Msg(mixed)) == "ab"


def test_balanced_json_extracts_first_object():
    assert _balanced_json('noise {"a": 1} tail') == '{"a": 1}'
    # brace inside a string literal must not end the object early
    assert _balanced_json('{"k": "}{"} ') == '{"k": "}{"}'
    assert _balanced_json("no json here") is None
