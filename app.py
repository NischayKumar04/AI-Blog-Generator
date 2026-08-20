"""AI Blog Generator — Streamlit entry point.

Flow: topic in -> `db.service.generate_and_save` (runs the LangGraph pipeline and
persists the row, streaming phase-level progress) -> render the result. A sidebar
lists past generations from the DB; clicking one reloads it.

Run locally:  streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from db import get_generation, init_db
from db.service import generate_and_save
from ui.components import (
    render_blog,
    render_meta,
    render_model_picker,
    render_topic_input,
)
from ui.history import show_history_sidebar
from ui.theme import inject_theme

st.set_page_config(page_title="AI Blog Generator", page_icon="🧠", layout="wide")

# create tables once per process (idempotent)
init_db()
inject_theme()

if "selected_id" not in st.session_state:
    st.session_state.selected_id = None
if "generating" not in st.session_state:
    st.session_state.generating = False
if "pending" not in st.session_state:
    st.session_state.pending = None
if "run_error" not in st.session_state:
    st.session_state.run_error = None


def _run_generation(topic: str, provider: str, model: str) -> str:
    """Run the pipeline with live phase-level progress. Returns the new row id."""
    seen: set[str] = set()
    with st.status(f"Generating “{topic}” …", expanded=True) as status:

        def on_progress(node: str, label: str) -> None:
            # workers fan out -> the "worker" node fires many times; show it once
            if node in seen:
                return
            seen.add(node)
            st.write(f"✅ {label}")

        gen = generate_and_save(
            topic,
            provider=provider,
            model=model,
            on_progress=on_progress,
            ensure_schema=False,
        )

        if gen.status == "completed":
            status.update(label="Done ✓", state="complete")
        else:
            status.update(label="Generation failed", state="error")
    return str(gen.id)


# ---- sidebar (sets st.session_state.selected_id) ----
show_history_sidebar()

# ---- header ----
st.markdown(
    "<h1><span class='bg-title'>AI Blog Generator</span></h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p class='muted'>Multi-agent technical blog writer — research, plan, "
    "write, and diagram, end to end.</p>",
    unsafe_allow_html=True,
)

# ---- input + generate ----
# Two-phase submit so the button visibly locks while a generation runs:
#   phase 1 (click)  -> stash inputs, flip `generating`, rerun to paint disabled
#   phase 2 (rerun)  -> run the (blocking) pipeline, then clear the flag + rerun
busy = st.session_state.generating
provider, model = render_model_picker(disabled=busy)
topic, submitted = render_topic_input(disabled=busy)

if submitted and not busy:
    st.session_state.generating = True
    st.session_state.pending = {"topic": topic, "provider": provider, "model": model}
    st.rerun()

if st.session_state.generating and st.session_state.pending:
    job = st.session_state.pending
    try:
        new_id = _run_generation(job["topic"], job["provider"], job["model"])
        st.session_state.selected_id = new_id
        st.session_state.run_error = None
    except Exception as exc:  # non-pipeline failure (e.g. DB write) — never crash the page
        st.session_state.run_error = str(exc)
    finally:
        st.session_state.pending = None
        st.session_state.generating = False
    st.rerun()

# surface an unexpected (non-pipeline) error from the last run attempt
if st.session_state.get("run_error"):
    st.error(f"Could not complete the generation: {st.session_state.run_error}")

# ---- display selected / most-recent generation ----
selected_id = st.session_state.get("selected_id")
if selected_id:
    gen = get_generation(selected_id)
    if gen is None:
        st.warning("That generation no longer exists.")
    elif gen.status == "failed":
        render_meta(gen)
        msg = gen.error_message or "Unknown error."
        st.error(f"Generation failed: {msg}")
        low = msg.lower()
        if any(k in low for k in ("rate", "429", "quota", "token limit", "tokens per")):
            st.info(
                "This looks like a rate/token limit. Wait a minute and try again, "
                "or pick a different model from the dropdown above."
            )
    elif gen.final_markdown:
        st.markdown(f"## {gen.blog_title or gen.topic}")
        render_meta(gen)
        st.download_button(
            "📥 Download Markdown",
            data=gen.final_markdown,
            file_name=f"{(gen.blog_title or gen.topic)[:60]}.md",
            mime="text/markdown",
        )
        st.markdown("<div class='blog-card'>", unsafe_allow_html=True)
        render_blog(gen.final_markdown)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info(f"Status: {gen.status} — nothing to show yet.")
else:
    st.caption("Enter a topic above to generate your first blog.")
