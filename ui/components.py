"""Reusable UI widgets: topic input, progress, and the blog renderer.

The blog renderer is the interesting one. Streamlit's ``st.markdown`` does NOT
render Mermaid — a ```mermaid block would show as a code block. So we split the
final markdown on ```mermaid fences and interleave:
  * prose  -> ``st.markdown`` (native styling, code blocks, etc.)
  * diagram -> an inline Mermaid renderer in a ``components.html`` iframe.
"""

from __future__ import annotations

import html
import re
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components

from core.llm import AVAILABLE_MODELS

EXAMPLE_TOPICS = [
    "Self Attention in Transformer Architecture",
    "How Rust's borrow checker prevents data races",
    "Designing an idempotent payments API",
]

# matches a fenced ```mermaid ... ``` block; group(1) is the raw diagram code
_MERMAID_FENCE = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)


def render_topic_input(disabled: bool = False) -> tuple[str, bool]:
    """Render the topic box + Generate button.

    Returns ``(topic, submitted)`` where ``submitted`` is True only on the run
    where the button was clicked with a non-empty topic. Pass ``disabled=True``
    to lock both widgets (e.g. while a generation is running).
    """
    topic = st.text_input(
        "Blog topic",
        placeholder=f"e.g. {EXAMPLE_TOPICS[0]}",
        label_visibility="collapsed",
        disabled=disabled,
    )
    col1, _ = st.columns([1, 4])
    with col1:
        clicked = st.button(
            "🚀 Generate",
            type="primary",
            use_container_width=True,
            disabled=disabled,
        )
    submitted = clicked and bool(topic.strip())
    if clicked and not topic.strip():
        st.warning("Enter a topic first.")
    return topic.strip(), submitted


def render_model_picker(disabled: bool = False) -> tuple[str, str]:
    """Render the LLM provider+model dropdown. Returns ``(provider, model)``.

    Options come from ``core.llm.AVAILABLE_MODELS`` (single source of truth); the
    first entry — Groq gpt-oss-20b — is the default selection.
    """
    labels = [label for label, _, _ in AVAILABLE_MODELS]
    choice = st.selectbox(
        "Model",
        options=range(len(AVAILABLE_MODELS)),
        format_func=lambda i: labels[i],
        index=0,
        disabled=disabled,
        help="Pick the LLM used for this run. Groq is the default; switch to "
        "Google Gemini if you hit Groq's rate limits.",
    )
    _, provider, model = AVAILABLE_MODELS[choice]
    return provider, model


def _mermaid(code: str) -> None:
    """Render one Mermaid diagram in a self-contained iframe.

    Height is estimated from the diagram's orientation + edge count (a left-right
    flowchart stays short; a top-down one grows with nodes). The diagram is
    centered both axes so any residual slack reads as intentional padding, and
    ``scrolling`` covers the rare underestimate.
    """
    horizontal = bool(re.search(r"\b(?:graph|flowchart)\s+(?:lr|rl)\b", code, re.I))
    edges = len(re.findall(r"--+>|==+>|--+|-\.->", code))
    if horizontal:
        height = max(200, min(520, 150 + edges * 14))
    else:
        height = max(240, min(900, 150 + edges * 46))

    safe = html.escape(code, quote=False)
    doc = f"""
    <!DOCTYPE html><html><head>
      <script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
      <style>
        html,body {{ height:100%; margin:0; background:#1a1a2e; }}
        .wrap {{ height:100%; display:flex; align-items:center; justify-content:center;
                 padding:12px; box-sizing:border-box; }}
        .mermaid svg {{ max-width:100%; height:auto; }}
      </style>
    </head><body>
      <div class="wrap"><pre class="mermaid">{safe}</pre></div>
      <script>
        mermaid.initialize({{
          startOnLoad: true, theme: 'dark', securityLevel: 'loose',
          themeVariables: {{ fontSize: '15px' }}
        }});
      </script>
    </body></html>
    """
    components.html(doc, height=height, scrolling=True)


def render_blog(markdown: str) -> None:
    """Render blog markdown, swapping ```mermaid fences for real diagrams."""
    if not markdown:
        st.info("No content.")
        return

    pos = 0
    for m in _MERMAID_FENCE.finditer(markdown):
        prose = markdown[pos:m.start()]
        if prose.strip():
            st.markdown(prose)
        code = m.group(1).strip()
        if code:
            _mermaid(code)
        pos = m.end()

    tail = markdown[pos:]
    if tail.strip():
        st.markdown(tail)


def render_meta(gen) -> None:
    """A row of small chips summarizing a generation."""
    chips = []
    if getattr(gen, "llm_model", None):
        chips.append(f"<span class='chip'>model <b>{gen.llm_model}</b></span>")
    if gen.mode:
        chips.append(f"<span class='chip'>mode <b>{gen.mode}</b></span>")
    if gen.blog_kind:
        chips.append(f"<span class='chip'>kind <b>{gen.blog_kind}</b></span>")
    if gen.section_count is not None:
        chips.append(f"<span class='chip'>sections <b>{gen.section_count}</b></span>")
    if gen.word_count is not None:
        chips.append(f"<span class='chip'>words <b>{gen.word_count}</b></span>")
    if gen.diagram_count is not None:
        chips.append(f"<span class='chip'>diagrams <b>{gen.diagram_count}</b></span>")
    if gen.duration_seconds is not None:
        chips.append(f"<span class='chip'>took <b>{gen.duration_seconds:.0f}s</b></span>")
    if chips:
        st.markdown("".join(chips), unsafe_allow_html=True)
