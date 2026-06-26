---
name: okf-wiki-builder
description: Create or maintain an OKF-compatible LLM Wiki Bundle from source files, preserving raw materials, writing Markdown concepts with OKF frontmatter, directory indexes, source summaries, asset metadata, questions, and typed graph relationships.
---

# OKF Wiki Builder

Use this skill when creating or maintaining an OKF-compatible LLM Wiki Bundle.

This skill is the OKF-aligned builder layer. It does not replace `llm-wiki-builder`; it refines its output format so the knowledge base can be consumed as a portable OKF-style bundle.

## Bundle Contract

Use this structure:

```text
bundle/
  index.md
  log.md
  graph.yml
  concepts/
    index.md
  sources/
    index.md
  assets/
    index.md
  questions/
    index.md
  maps/
    index.md
  raw/
    sources/
    private/
    assets/
```

## Frontmatter Contract

Every non-reserved Markdown concept page must include:

```yaml
---
type: Concept
title: Example
description: One-sentence summary for index/search previews.
resource: bundle://stable-resource-id-or-file-path
tags:
  - tag
timestamp: 2026-06-25T00:00:00+08:00
sources: []
---
```

`index.md` and `log.md` are reserved files. Root `index.md` may include `okf_version`.

## Workflow

1. Preserve raw files under `raw/sources/`, `raw/private/`, or `raw/assets/`.
2. Extract searchable text with `scripts/extract_source_text.py` when needed. For Office files, pass `--asset-dir raw/assets` so embedded media is preserved.
3. Create searchable asset metadata page drafts under `assets/` with `scripts/create_asset_pages.py`.
4. Create source summary pages under `sources/`.
5. Create concept pages under `concepts/`.
6. Create or refine asset metadata pages under `assets/` for diagrams, screenshots, charts, or media.
7. Create durable answers under `questions/` only when requested or clearly reusable.
8. Create maps under `maps/` for navigation.
9. Use standard Markdown links when possible.
10. Add `# Citations` to pages that make sourced claims.
11. Maintain `graph.yml` for typed relationships, including asset nodes and `illustrates` / `extracted_from` edges.
12. Regenerate directory-level `index.md` files for progressive disclosure.
13. Append to `log.md`.

## Image and OCR Rule

Do not require local OCR packages. For images:

1. Store the original image in `raw/assets/`.
2. Create an asset metadata page in `assets/`.
3. Include `resource`, `mime_type`, `description`, tags, citations, and related links.
4. If OCR text is available from the company agent OCR skill, add it under `# Visible Text`.
5. If OCR is unavailable, state that visual interpretation has not been performed.

For Office sources with embedded images, use:

```bash
python scripts/extract_source_text.py source.docx extracted.txt --asset-dir raw/assets
python scripts/create_asset_pages.py . --source-page sources/source-example.md
```

The first command preserves embedded media from Office internal folders such as `word/media/`, `ppt/media/`, and `xl/media/`. The second command creates OKF-compatible asset metadata pages so images become searchable knowledge objects.

An image file in `raw/assets/` without a matching `assets/asset-*.md` page is not sufficiently searchable.

## Quality Rules

- Prefer small, focused pages.
- Use `description` so indexes and search snippets are useful.
- Preserve uncertainty.
- Never mutate raw source files during ingest.
- Keep bundle links portable.
- Treat unknown OKF frontmatter fields as allowed extensions.

## Bundled Scripts

- `scripts/extract_source_text.py`: extract searchable text and preserve embedded Office media when `--asset-dir` is supplied.
- `scripts/create_asset_pages.py`: scan `raw/assets/` and create OKF-compatible `assets/asset-*.md` metadata page drafts.
