# AI Blog Generator

A multi-agent technical-blog generator built with **LangGraph**. It plans a post,
writes the sections in parallel, researches fresh facts with **Tavily** when a
topic needs them, and adds explanatory **Mermaid diagrams** — each validated
before it ships.

## How it works

```
router → (research) → orchestrator → parallel section writers → reducer (merge → diagrams)
```

- **Router** — decides whether web research is needed: `closed_book` (evergreen),
  `hybrid` (mostly evergreen + fresh examples), or `open_book` (news roundup).
- **Research** (Tavily) — gathers and de-duplicates evidence for fresh claims.
- **Orchestrator** — produces a structured outline of 5–9 sections.
- **Workers** — write each section in parallel via LangGraph `Send`.
- **Reducer** — merges the sections, proposes up to 3 **Mermaid diagrams**,
  validates each against a renderer, and drops any that don't render.

The final post is written to `outputs/` as Markdown with inline ```mermaid blocks
that render natively on GitHub and VS Code.

## Notebooks

The three notebooks are an evolution of the same idea:

| Notebook | Stage | Highlights |
| --- | --- | --- |
| `Notebooks/1_basic.ipynb` | MVP | orchestrator → parallel workers → reducer (local Ollama) |
| `Notebooks/2_Research.ipynb` | + research | Tavily research, routing, recency filtering (local Ollama) |
| `Notebooks/3_Image.ipynb` | **current** | full pipeline: **Groq** text generation + validated **Mermaid** diagrams |

## Setup

```bash
pip install -r requirements.txt
pip install langchain-groq
```

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_key      # console.groq.com  (text generation)
TAVILY_API_KEY=your_tavily_key  # tavily.com        (research)
```

> The older notebooks (`1_basic`, `2_Research`) use a local **Ollama** server
> instead of Groq — run `ollama pull qwen3:14b` and start Ollama if you want those.

## Run

```bash
jupyter notebook   # open Notebooks/3_Image.ipynb and run top-to-bottom
```

Then call the runner with a topic:

```python
out = run("Self Attention in Transformer Architecture")
```

## Notes

- Diagrams are validated via the [kroki](https://kroki.io) Mermaid renderer; only a
  definitive syntax error drops a diagram, and transient renderer errors fail open.
- See [`WORKLOG.md`](WORKLOG.md) for the change history and known open items.
