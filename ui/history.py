"""History sidebar — lists past generations from the DB and handles selection.

Selection is communicated via ``st.session_state.selected_id`` (a string UUID or
None). Clicking an item sets it and reruns; ``app.py`` reads it to decide what to
show in the main pane.
"""

from __future__ import annotations

import streamlit as st

from db import delete_all_generations, delete_generation, list_generations

_STATUS_ICON = {
    "completed": "✅",
    "failed": "❌",
    "running": "🔄",
    "pending": "⏳",
}


def show_history_sidebar() -> None:
    with st.sidebar:
        st.markdown("### 🧠 AI Blog Generator")
        if st.button("➕  New blog", use_container_width=True):
            st.session_state.selected_id = None
            st.rerun()

        st.markdown("#### History")
        rows = list_generations(limit=50)
        if not rows:
            st.caption("No generations yet.")
            return

        for row in rows:
            icon = _STATUS_ICON.get(row.status, "•")
            label = (row.blog_title or row.topic or "untitled").strip()
            if len(label) > 32:
                label = label[:31] + "…"
            open_col, del_col = st.columns([5, 1])
            with open_col:
                if st.button(
                    f"{icon}  {label}", key=f"hist-{row.id}", use_container_width=True
                ):
                    st.session_state.selected_id = str(row.id)
                    st.rerun()
            with del_col:
                if st.button("🗑", key=f"del-{row.id}", help="Delete this blog"):
                    delete_generation(row.id)
                    if st.session_state.get("selected_id") == str(row.id):
                        st.session_state.selected_id = None
                    st.rerun()

        st.divider()
        _render_clear_control()


def _render_clear_control() -> None:
    """A 🗑 Clear-history button gated behind an inline two-click confirmation."""
    if st.session_state.get("confirm_clear"):
        st.caption("Delete **all** saved generations? This can't be undone.")
        yes, no = st.columns(2)
        with yes:
            if st.button("✅ Yes", use_container_width=True, key="clear-yes"):
                delete_all_generations()
                st.session_state.confirm_clear = False
                st.session_state.selected_id = None
                st.rerun()
        with no:
            if st.button("✖ Cancel", use_container_width=True, key="clear-no"):
                st.session_state.confirm_clear = False
                st.rerun()
    elif st.button("🗑  Clear history", use_container_width=True, key="clear-history"):
        st.session_state.confirm_clear = True
        st.rerun()
