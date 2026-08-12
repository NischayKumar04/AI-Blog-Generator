"""Mermaid cleanup + validation helpers.

Isolated from the reducer so they can be unit-tested without a graph or an LLM.
Extracted from Notebooks/3_Image.ipynb (cell 7).
"""

from __future__ import annotations

import time

import requests

KROKI_MERMAID_URL = "https://kroki.io/mermaid/svg"


def _clean_mermaid(code: str) -> str:
    """Normalize LLM-produced Mermaid into valid, renderable code."""
    code = (code or "").strip()

    # 1) Strip accidental ``` fences / language tags.
    if code.startswith("```"):
        lines = code.splitlines()
        if lines and lines[0].startswith("```"):        # drop opening ``` / ```mermaid
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):  # drop closing ```
            lines = lines[:-1]
        code = "\n".join(lines).strip()

    # 2) Repair a common LLM mistake: labeled edges written as `-->|text|>`.
    #    Valid Mermaid is `-->|text|` (no trailing '>'). Verified against a
    #    real renderer: the trailing '>' returns a hard HTTP 400.
    code = code.replace("|>", "|")

    # 3) Split a ';'-separated single line onto its own lines. Semicolons are
    #    valid Mermaid, but the one-line form is unreadable and some renderers
    #    dislike it; the model also ignores the "no semicolons" instruction.
    if ";" in code:
        parts = [p.strip() for p in code.split(";") if p.strip()]
        if parts:
            header, *rest = parts
            code = header + "\n" + "\n".join("    " + r for r in rest)

    return code


def _mermaid_ok(src: str) -> bool:
    """True if the Mermaid renders. Validate via kroki; only a definitive HTTP
    400 counts as invalid. kroki's 500s are flaky, so retry to reach a real
    200/400, and fail OPEN if we never do (a hiccup must not strip good diagrams).
    """
    for _ in range(3):
        try:
            r = requests.post(
                KROKI_MERMAID_URL,
                data=src.encode("utf-8"),
                timeout=30,
            )
            if r.status_code == 400:   # definitive syntax error
                return False
            if r.status_code == 200:   # definitely renders
                return True
            # 5xx -> transient, retry
        except Exception:
            pass
        time.sleep(1)
    return True  # no definitive answer -> keep it (fail-open)
