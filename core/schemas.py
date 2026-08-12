"""Pydantic schemas for the blog-generation pipeline.

Extracted verbatim from Notebooks/3_Image.ipynb (cell 1). These models define
the router decision, the section plan, research evidence, and the diagram plan.
"""

from __future__ import annotations

from typing import List, Optional, Literal

from pydantic import BaseModel, Field


class Task(BaseModel):
    id: int
    title: str

    goal: str = Field(
        ...,
        description="One sentence describing what the reader should be able to do/understand after this section.",
    )
    bullets: List[str] = Field(
        ...,
        min_length=3,
        max_length=6,
        description="3–6 concrete, non-overlapping subpoints to cover in this section.",
    )
    target_words: int = Field(..., description="Target word count for this section (120–550).")

    tags: List[str] = Field(default_factory=list)
    requires_research: bool = False
    requires_citations: bool = False
    requires_code: bool = False


class Plan(BaseModel):
    blog_title: str
    audience: str
    tone: str
    blog_kind: Literal["explainer", "tutorial", "news_roundup", "comparison", "system_design"] = "explainer"
    constraints: List[str] = Field(default_factory=list)
    tasks: List[Task]


class EvidenceItem(BaseModel):
    title: str
    url: str
    published_at: Optional[str] = None  # keep if Tavily provides; DO NOT rely on it
    snippet: Optional[str] = None
    source: Optional[str] = None


class RouterDecision(BaseModel):
    needs_research: bool
    mode: Literal["closed_book", "hybrid", "open_book"]
    queries: List[str] = Field(default_factory=list)


class EvidencePack(BaseModel):
    evidence: List[EvidenceItem] = Field(default_factory=list)


class DiagramSpec(BaseModel):
    placeholder: str = Field(..., description="e.g. [[DIAGRAM_1]]")
    title: str = Field(..., description="Short caption shown under the diagram.")
    mermaid: str = Field(..., description="Valid Mermaid diagram code (raw, no ``` fences).")


class GlobalDiagramPlan(BaseModel):
    md_with_placeholders: str
    diagrams: List[DiagramSpec] = Field(default_factory=list)
