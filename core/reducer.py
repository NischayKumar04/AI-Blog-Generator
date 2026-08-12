"""Reducer subgraph — merge sections, decide + validate inline Mermaid diagrams,
then place them.

    merge_content -> decide_images -> generate_and_place_images

Diagrams are inline Mermaid (free, deterministic; validated via kroki). Extracted
from Notebooks/3_Image.ipynb (cells 7–8).

Change vs notebook: this no longer writes a `.md` file to disk. The pipeline
returns the final Markdown in state["final"]; persistence is the caller's job
(the runner's optional `output_path`, or the DB layer).
"""

from __future__ import annotations

import logging

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END

from .llm import get_llm
from .mermaid_utils import _clean_mermaid, _mermaid_ok
from .schemas import GlobalDiagramPlan
from .state import State

logger = logging.getLogger(__name__)


def merge_content(state: State) -> dict:
    plan = state["plan"]

    ordered_sections = [md for _, md in sorted(state["sections"], key=lambda x: x[0])]
    body = "\n\n".join(ordered_sections).strip()
    merged_md = f"# {plan.blog_title}\n\n{body}\n"
    return {"merged_md": merged_md}


DECIDE_DIAGRAMS_SYSTEM = """You are an expert technical editor.
Decide whether diagrams would materially help readers understand THIS blog,
then express each one as a Mermaid diagram.

Rules:
- Max 3 diagrams total. Add a diagram ONLY where it clarifies a flow,
  architecture, process, or relationship that prose/code handles poorly.
- Insert placeholders exactly: [[DIAGRAM_1]], [[DIAGRAM_2]], [[DIAGRAM_3]],
  each on its own line at the most relevant spot in the markdown.
- If no diagrams help: md_with_placeholders must EQUAL the input and diagrams=[].

Mermaid rules (CRITICAL — output must be VALID Mermaid that renders on GitHub):
- Pick the fitting type: flowchart (`graph TD` / `graph LR`), `sequenceDiagram`,
  `stateDiagram-v2`, `classDiagram`, or `erDiagram`.
- Put ONLY raw Mermaid code in the `mermaid` field. Do NOT wrap it in ``` fences.
- Put EACH statement on its own line. Do NOT cram the whole graph onto one line
  and do NOT use ';' as a separator.
- For a labeled edge use EXACTLY this form:  A -->|"label"| B
  The label is closed by a single '|' followed by the target node.
  NEVER write a trailing '>' after the label (i.e. `A -->|label|> B` is WRONG).
- Keep node labels short. Wrap any label with spaces/special chars in double
  quotes, e.g.  A["Scaled dot-product"] --> B["Softmax"].
- Avoid raw parentheses or unquoted punctuation inside labels.
- Prefer 4–12 nodes; keep it readable, not exhaustive.

Example of a valid diagram:
graph LR
    A["Input"] -->|"Query"| B["Q vector"]
    A -->|"Key"| C["K vector"]
    B --> D["Attention scores"]
    C --> D

Return strictly GlobalDiagramPlan.
"""


def decide_images(state: State) -> dict:
    planner = get_llm().with_structured_output(GlobalDiagramPlan)
    merged_md = state["merged_md"]
    plan = state["plan"]
    assert plan is not None

    diagram_plan = planner.invoke(
        [
            SystemMessage(content=DECIDE_DIAGRAMS_SYSTEM),
            HumanMessage(
                content=(
                    f"Blog kind: {plan.blog_kind}\n"
                    f"Topic: {state['topic']}\n\n"
                    "Insert placeholders + propose Mermaid diagrams.\n\n"
                    f"{merged_md}"
                )
            ),
        ]
    )

    return {
        "md_with_placeholders": diagram_plan.md_with_placeholders,
        "diagram_specs": [d.model_dump() for d in diagram_plan.diagrams],
    }


def generate_and_place_images(state: State) -> dict:
    plan = state["plan"]
    assert plan is not None

    md = state.get("md_with_placeholders") or state["merged_md"]
    diagram_specs = state.get("diagram_specs", []) or []

    for spec in diagram_specs:
        placeholder = spec["placeholder"]
        mermaid = _clean_mermaid(spec.get("mermaid", ""))
        title = (spec.get("title") or "").strip()

        # Empty diagram -> just remove the placeholder, keep doc clean.
        if not mermaid:
            md = md.replace(placeholder, "")
            continue

        # Never ship a syntax-broken diagram.
        if not _mermaid_ok(mermaid):
            logger.warning("Dropping invalid Mermaid at %s", placeholder)
            md = md.replace(placeholder, "")
            continue

        block = f"```mermaid\n{mermaid}\n```"
        if title:
            block += f"\n*{title}*"
        md = md.replace(placeholder, block)

    return {"final": md}


def build_reducer_subgraph():
    """Compile and return the reducer subgraph."""
    reducer_graph = StateGraph(State)
    reducer_graph.add_node("merge_content", merge_content)
    reducer_graph.add_node("decide_images", decide_images)
    reducer_graph.add_node("generate_and_place_images", generate_and_place_images)
    reducer_graph.add_edge(START, "merge_content")
    reducer_graph.add_edge("merge_content", "decide_images")
    reducer_graph.add_edge("decide_images", "generate_and_place_images")
    reducer_graph.add_edge("generate_and_place_images", END)
    return reducer_graph.compile()
