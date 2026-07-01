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
- `get_asset_file`
- `find_applicable_assets`

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
9. Do not attach images from source/concept pages automatically.
10. Call `find_applicable_assets` with the user question and matched page paths.
11. Use only ready assets returned by `find_applicable_assets`. If the user explicitly asks for images and no applicable asset is returned, say the bundle has no question-matched image evidence.
12. `find_applicable_assets` rejects draft assets and weak keyword-only matches. Do not override that by using `search_assets` or `get_page_assets` to attach images.
13. When an applicable asset should be displayed, call `get_asset_file` with the returned asset page or `raw/assets/...` path to retrieve the displayable file metadata and base64 payload. Do not assume RAG text contains the image body.
14. If image OCR/visual understanding is needed to answer, call the company's OCR/image skill on the asset path returned by MCP before citing visual evidence.
15. Answer with citations to concept, source, and applicable asset pages.

## Rules

- Do not answer company knowledge questions from model memory alone.
- Do not answer from isolated chunks alone.
- Do not require `ripgrep` / `rg`.
- Do not require local OCR.
- Read complete pages before finalizing an answer; snippets are only for candidate selection.
- Cite `# Citations` sources when evidence matters.
- If evidence is missing, say the bundle does not contain enough evidence.
- Do not present draft asset metadata as finalized evidence.
- Do not include images merely because they share a source, heading, concept, or search result with the answer.
- Include images only when `find_applicable_assets` returns them or when a matched question page explicitly lists them in `# Assets Used`.
- To display an allowed image, use `get_asset_file`; `rag-upload` only contains image policy and asset references, not the image body.
- `get_asset_file` accepts either `assets/asset-example.md` or `raw/assets/example.png`. Prefer the asset page path when available because it preserves metadata context.

## Answer Format

```text
Answer...

Sources:
- concepts/example.md
- sources/source-example.md

Assets:
- assets/asset-example-diagram.md
- raw/assets/example-diagram.png
- get_asset_file returned image/png payload for raw/assets/example-diagram.png
```
