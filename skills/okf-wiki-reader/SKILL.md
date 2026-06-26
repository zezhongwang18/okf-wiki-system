---
name: okf-wiki-reader
description: Use when answering questions from an OKF-compatible LLM Wiki Bundle through MCP tools, including bundle indexes, concept pages, source summaries, typed graph relationships, and image/media assets.
---

# OKF Wiki Reader

Use this skill when the user asks about knowledge that may be contained in an OKF-compatible LLM Wiki Bundle.

## Required MCP Server

Prefer an MCP server exposing OKF bundle tools.

Expected tools:

- `get_bundle_status`
- `list_bundle_index`
- `list_directory_index`
- `search_bundle`
- `read_concept`
- `get_related_links`
- `get_backlinks`
- `search_assets`
- `get_page_assets`
- `read_asset_metadata`

## Query Triggers

Search the bundle first when the user asks about:

- company knowledge
- internal processes
- product or project context
- historical decisions
- reusable methods
- training materials
- source-backed answers
- "what did we say before"
- "is there anything in the wiki"

## Query Workflow

1. Call `get_bundle_status`.
2. Call `list_bundle_index` to read the root index.
3. If the topic maps to a subdirectory, call `list_directory_index`.
4. For complex questions, generate 2-3 search variants:
   - direct user wording
   - domain synonym query
   - broader category query
5. Call `search_bundle` for the query variants.
6. Deduplicate and rank results.
7. Read complete pages with `read_concept`.
8. Use `get_related_links` and `get_backlinks` to traverse the bundle graph.
9. Use `get_page_assets` and `search_assets` when diagrams, screenshots, charts, or figures may help.
10. If image OCR or visual understanding is needed, call the company's OCR/image skill on the asset path returned by MCP.
11. Answer with citations to concept, source, and asset pages.

## Rules

- Do not answer company knowledge questions from model memory alone.
- Do not answer from isolated chunks alone.
- Do not require `ripgrep` / `rg`.
- Do not require local OCR.
- Prefer complete pages over snippets.
- Cite `# Citations` sources when evidence matters.
- If evidence is missing, say the bundle does not contain enough evidence.

## Answer Format

```text
Answer...

Sources:
- concepts/example.md
- sources/source-example.md

Assets:
- assets/asset-example-diagram.md
- raw/assets/example-diagram.png
```
