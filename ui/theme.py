"""Dark-theme polish injected on top of `.streamlit/config.toml`.

The base palette lives in `.streamlit/config.toml` (`[theme]`). This module adds
supplementary CSS for a more "premium" feel: gradient title, carded blog output,
tighter sidebar buttons, and accent hover states. Called once from `app.py`.
"""

from __future__ import annotations

import streamlit as st

# accent palette (kept in sync with .streamlit/config.toml)
ACCENT = "#e94560"
BG = "#0f0f1a"
CARD = "#1a1a2e"
CARD_2 = "#16213e"
TEXT = "#e6e6f0"
MUTED = "#9aa0b4"

_CSS = f"""
<style>
/* ---- layout ---- */
.block-container {{ padding-top: 2.2rem; max-width: 1100px; }}

/* ---- gradient title ---- */
h1 span.bg-title {{
    background: linear-gradient(90deg, {ACCENT}, #8a5cf6 60%, #3fa9f5);
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800; letter-spacing: -0.02em;
}}

/* ---- primary button ---- */
.stButton > button[kind="primary"], .stButton > button[data-testid="baseButton-primary"] {{
    background: linear-gradient(90deg, {ACCENT}, #b3324a);
    border: 0; color: #fff; font-weight: 600; border-radius: 10px;
    transition: transform .06s ease, box-shadow .2s ease;
}}
.stButton > button[kind="primary"]:hover {{
    transform: translateY(-1px);
    box-shadow: 0 6px 18px rgba(233,69,96,.35);
}}

/* ---- sidebar history buttons: full width, left aligned, compact ---- */
section[data-testid="stSidebar"] .stButton > button {{
    width: 100%; text-align: left; justify-content: flex-start;
    background: {CARD_2}; border: 1px solid rgba(255,255,255,.06);
    border-radius: 8px; color: {TEXT}; font-weight: 500;
    padding: .45rem .6rem; margin-bottom: .3rem;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}
section[data-testid="stSidebar"] .stButton > button:hover {{
    border-color: {ACCENT}; color: #fff;
}}

/* ---- blog output card ---- */
.blog-card {{
    background: {CARD}; border: 1px solid rgba(255,255,255,.06);
    border-radius: 14px; padding: 1.6rem 2rem; margin-top: 1rem;
}}

/* ---- meta chips row ---- */
.chip {{
    display: inline-block; background: {CARD_2}; color: {MUTED};
    border: 1px solid rgba(255,255,255,.06); border-radius: 999px;
    padding: .18rem .7rem; margin: 0 .35rem .4rem 0; font-size: .82rem;
}}
.chip b {{ color: {TEXT}; font-weight: 600; }}

/* ---- caption / muted text ---- */
.muted {{ color: {MUTED}; font-size: .9rem; }}
</style>
"""


def inject_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
