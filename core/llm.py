"""LLM provider setup.

`get_llm()` is a lazily-instantiated, cached factory so that:
  * importing any pipeline module does NOT require GROQ_API_KEY (tests can
    import freely and inject a fake by populating the cache);
  * the model / temperature are configurable via env vars.

Tests can override the LLM by setting `core.llm._llm = <fake>` before the first
node runs, or by monkeypatching `get_llm`.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

# Default: Groq free tier. Swap via GROQ_MODEL for any tool-calling model on
# https://console.groq.com/docs/models (e.g. "openai/gpt-oss-120b").
DEFAULT_MODEL = "llama-3.3-70b-versatile"

_llm = None


def get_llm():
    """Return a process-wide cached chat model, building it on first use."""
    global _llm
    if _llm is None:
        _llm = ChatGroq(
            model=os.getenv("GROQ_MODEL", DEFAULT_MODEL),
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=float(os.getenv("GROQ_TEMPERATURE", "0")),
        )
    return _llm


def reset_llm() -> None:
    """Clear the cached model (useful in tests or after changing env)."""
    global _llm
    _llm = None
