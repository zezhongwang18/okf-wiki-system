---
name: okf-wiki-reader
description: Use when answering questions from an OKF-compatible LLM Wiki Bundle through MCP tools, including bundle indexes, concept pages, source summaries, typed graph relationships, and image/media assets.
---

# OKF Wiki Reader

Use this skill when the user asks about knowledge that may be contained in an OKF-compatible LLM Wiki Bundle.

## Required MCP Server

Use the OKF MCP server when these tools are available. If the server is unavailable, report that the bundle cannot be queried instead of answering from memory.

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
9. If the question mentions or implies diagrams, screenshots, charts, figures, UI states, visual evidence, or attached images, call `get_page_assets` and `search_assets`.
10. If returned asset metadata has empty TODO fields, or if image OCR/visual understanding is needed to answer, call the company's OCR/image skill on the asset path returned by MCP.
11. If `read_asset_metadata` returns `completion_status: draft` or `has_todo: true`, treat the asset description as unfinished. Use the original image path and OCR/image skill before citing it as evidence.
12. Answer with citations to concept, source, and asset pages.

## Rules

- Do not answer company knowledge questions from model memory alone.
- Do not answer from isolated chunks alone.
- Do not require `ripgrep` / `rg`.
- Do not require local OCR.
- Read complete pages before finalizing an answer; snippets are only for candidate selection.
- Cite `# Citations` sources when evidence matters.
- If evidence is missing, say the bundle does not contain enough evidence.
- Do not present draft asset metadata as finalized evidence.

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
