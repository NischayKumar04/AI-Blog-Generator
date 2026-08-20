"""LLM provider setup — multi-provider, per-run selectable.

`get_llm()` builds a chat model for a ``(provider, model)`` pair and caches it by
key, so importing pipeline modules needs no API key. Nodes call ``get_llm()``
with no args and resolve the *active* selection set by ``set_active_llm()``
(falling back to the env default — Groq's gpt-oss-120b).

Resilience: every model is built with ``max_retries`` so the provider SDK
auto-waits on 429 rate limits (honoring ``Retry-After``) instead of hard-failing.

Tests inject a fake by setting ``core.llm._override = <fake>`` (or ``reset_llm()``).
"""

from __future__ import annotations

import ast
import json
import os
import re
from typing import Optional, Tuple

from dotenv import load_dotenv

load_dotenv()

# (label, provider, model) — the single source of truth for the UI dropdown.
# The first entry is the default selection.
AVAILABLE_MODELS = [
    ("Groq · gpt-oss-120b (default)", "groq", "openai/gpt-oss-120b"),
    ("Google · gemini-3.1-flash-lite", "google", "gemini-3.1-flash-lite"),
    ("Google · gemini-2.5-flash", "google", "gemini-2.5-flash"),
    ("Google · gemini-2.5-flash-lite", "google", "gemini-2.5-flash-lite"),
]

DEFAULT_SELECTION: Tuple[str, str] = (AVAILABLE_MODELS[0][1], AVAILABLE_MODELS[0][2])

_cache: dict[Tuple[str, str], object] = {}
_active: Optional[Tuple[str, str]] = None
_override = None  # test hook: when set, get_llm() returns it verbatim


def _build(provider: str, model: str):
    max_retries = int(os.getenv("LLM_MAX_RETRIES", "6"))
    temperature = float(os.getenv("LLM_TEMPERATURE", "0"))

    if provider == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=model,
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=temperature,
            max_retries=max_retries,
        )

    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=temperature,
            max_retries=max_retries,
        )

    raise ValueError(f"Unknown LLM provider: {provider!r}")


def get_llm(provider: Optional[str] = None, model: Optional[str] = None):
    """Return a cached chat model. With no args, uses the active selection.

    The cache is keyed by ``(provider, model)``, so switching models between runs
    reuses the compiled graph while picking up the newly selected model.
    """
    if _override is not None:
        return _override
    if provider is None or model is None:
        provider, model = _active or DEFAULT_SELECTION
    key = (provider, model)
    if key not in _cache:
        _cache[key] = _build(provider, model)
    return _cache[key]


def set_active_llm(provider: Optional[str], model: Optional[str]) -> None:
    """Set the (provider, model) that no-arg ``get_llm()`` calls will resolve to.

    Note: this is a process-wide global, which is fine under the app's
    one-generation-at-a-time rule but not safe for concurrent multi-user runs.
    """
    global _active
    if provider and model:
        _active = (provider, model)


def reset_llm() -> None:
    """Clear the cache, active selection, and any test override."""
    global _active, _override
    _cache.clear()
    _active = None
    _override = None


def message_text(message) -> str:
    """Flatten an LLM message's content to plain text.

    ``AIMessage.content`` is a plain string for most providers but a list of
    content blocks for others (notably Gemini 3.x, which returns e.g.
    ``[{"type": "text", "text": "..."}]``). This normalizes both shapes so
    callers can safely ``.strip()`` the result.
    """
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "".join(parts)
    return str(content)


# --- structured-output resilience -------------------------------------------

def _balanced_json(text: str) -> Optional[str]:
    """Return the first balanced ``{...}`` object in ``text`` (string-aware)."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _raw_generation(err: Exception) -> Optional[str]:
    """Extract a model's raw output from a provider error, if present.

    Groq's ``tool_use_failed`` (400) carries the offending generation under
    ``error.failed_generation``; fall back to scraping it from the string form.
    """
    body = getattr(err, "body", None)
    if isinstance(body, dict):
        gen = body.get("error", {}).get("failed_generation")
        if gen:
            return gen
    m = re.search(r"'failed_generation':\s*'(.*?)'\}\}", str(err), re.DOTALL)
    return m.group(1) if m else None


def _loads_lenient(text: str):
    """Parse ``text`` as JSON, falling back to a Python-literal eval.

    Small models sometimes emit Python-style literals (``False``/``True``/
    ``None``) or single quotes, which are invalid JSON but valid Python; those
    are recovered via ``ast.literal_eval``.
    """
    try:
        return json.loads(text)
    except Exception:
        pass
    try:
        return ast.literal_eval(text)
    except Exception:
        return None


def invoke_structured(schema, messages):
    """Invoke the active LLM for ``schema``, repairing small-model slips.

    Smaller models (notably Groq's llama-3.1-8b) sometimes emit malformed tool
    arguments — a stringified ``"false"`` for a boolean, or Python-style
    ``False``/``True``/``None`` literals — which Groq's server-side tool
    validation rejects with ``tool_use_failed``. We recover by pulling the
    model's raw output out of the error, parsing it leniently (JSON, then a
    Python-literal fallback), and re-validating through Pydantic, whose lax
    coercion normalizes the scalar types. Stronger models return on the happy
    path and never touch the repair branch.
    """
    llm = get_llm()
    try:
        return llm.with_structured_output(schema).invoke(messages)
    except Exception as err:
        raw = _raw_generation(err)
        candidate = _balanced_json(raw) if raw else None
        if candidate:
            obj = _loads_lenient(candidate)
            if isinstance(obj, dict):
                try:
                    return schema.model_validate(obj)
                except Exception:
                    pass
        raise
