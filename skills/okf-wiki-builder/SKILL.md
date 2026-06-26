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
2. Extract searchable text with `scripts/extract_source_text.py` for every non-plain-text source. For Office files, `--asset-dir raw/assets` is mandatory so embedded media is preserved.
3. Create searchable asset metadata page drafts under `assets/` with `scripts/create_asset_pages.py`.
4. Create source summary pages under `sources/`.
5. Create concept pages under `concepts/`.
6. Create or refine asset metadata pages under `assets/` for diagrams, screenshots, charts, or media using `# Source Context` first, then OCR/visual notes.
7. Create durable answers under `questions/` only when requested or clearly reusable.
8. Create maps under `maps/` for navigation.
9. Use standard Markdown links for internal bundle references unless a target page does not exist yet.
10. Add `# Citations` to pages that make sourced claims.
11. Maintain `graph.yml` for typed relationships, including asset nodes and `illustrates` / `extracted_from` edges.
12. Regenerate directory-level `index.md` files for progressive disclosure.
13. Run `scripts/validate_bundle.py bundle`.
14. Append to `log.md`.
15. Report completion only after validation passes.

## Mandatory Ingest Gates

For `.docx`, `.pptx`, `.xlsx`, and `.xlsm` sources, do not use `python-docx`, `python-pptx`, `openpyxl`, or ad hoc extraction as the complete ingest path. Those tools may miss embedded pictures.

Before writing source summaries or concept pages for an Office source, run the bundled extractor or an equivalent command that preserves embedded media:

```bash
python skills/okf-wiki-builder/scripts/extract_source_text.py bundle/raw/sources/source.docx bundle/raw/sources/source.extracted.txt --asset-dir bundle/raw/assets
python skills/okf-wiki-builder/scripts/create_asset_pages.py bundle --source-page sources/source-example.md
```

After running the commands, verify:

1. the extracted text file exists;
2. embedded media listed in the extracted text was copied to `bundle/raw/assets/`;
3. `bundle/raw/assets/asset_context.json` exists when Office media was extracted;
4. every image/media file in `bundle/raw/assets/` has a matching `bundle/assets/asset-*.md` page, unless it is explicitly marked as duplicate or non-knowledge-bearing in `log.md`;
5. image-heavy source summaries link to the relevant asset metadata pages.

If an Office file is known or expected to contain images but no assets are extracted, stop and report the extraction gap instead of silently continuing.

For standalone image files, copy them to `bundle/raw/assets/` first, then run `scripts/create_asset_pages.py` before answering or summarizing. A raw image without an asset metadata page is incomplete ingest.

## Completion Gate

Do not say ingest is complete while generated asset pages still contain `TODO`, `Source Page TODO`, `Concept TODO`, or `Context unavailable`, unless the user explicitly asks for a draft.

Before reporting completion, run:

```bash
python skills/okf-wiki-builder/scripts/validate_bundle.py bundle
```

If the user requested a draft ingest, run:

```bash
python skills/okf-wiki-builder/scripts/validate_bundle.py bundle --allow-drafts
```

When validation fails, report the failed checks and continue fixing them. Do not summarize a failed ingest as complete.

## Image Context Binding Rule

Asset descriptions must be grounded in source context. Do not describe an extracted image only from the file name or the whole document topic.

For authoring source documents, prefer this layout:

```text
Relevant body paragraphs
Figure title or caption
Image
```

During ingest, bind each image to the nearest preceding heading, caption, and previous body paragraphs. Treat following text as context only when it clearly looks like a caption. This avoids binding an image to an unrelated next section.

The bundled extractor writes `bundle/raw/assets/asset_context.json` for Office sources. The asset page generator reads it and writes a `# Source Context` section into each `assets/asset-*.md` page.

When filling `# Description`, `# Visible Text`, or `# Visual Notes`, use this order of evidence:

1. `# Source Context` from the asset page;
2. OCR/image-skill output;
3. manual visual inspection;
4. source summary and concepts.

If `source_context_available: false`, keep interpretation tentative and state that the image is not precisely bound to source text.

## Image and OCR Rule

Do not require local OCR packages. For images:

1. Store the original image in `raw/assets/`.
2. Create an asset metadata page in `assets/`.
3. Include `resource`, `mime_type`, `description`, tags, citations, and related links.
4. When the image contains visible text or is a diagram/screenshot/chart, call the company agent OCR/image skill if available and add the result under `# Visible Text` or `# Visual Notes`.
5. If OCR/image inspection is unavailable, state that visual interpretation has not been performed and keep the asset page as a TODO, not as completed analysis.

For Office sources with embedded images, use:

```bash
python skills/okf-wiki-builder/scripts/extract_source_text.py bundle/raw/sources/source.docx bundle/raw/sources/source.extracted.txt --asset-dir bundle/raw/assets
python skills/okf-wiki-builder/scripts/create_asset_pages.py bundle --source-page sources/source-example.md
```

The first command preserves embedded media from Office internal folders such as `word/media/`, `ppt/media/`, and `xl/media/`. The second command creates OKF-compatible asset metadata pages so images become searchable knowledge objects.

An image file in `raw/assets/` without a matching `assets/asset-*.md` page is incomplete ingest.

## Quality Rules

- Prefer small, focused pages.
- Use `description` so indexes and search snippets are useful.
- Preserve uncertainty.
- Never mutate raw source files during ingest.
- Keep bundle links portable.
- Treat unknown OKF frontmatter fields as allowed extensions.

## Bundled Scripts

- `scripts/extract_source_text.py`: extract searchable text, preserve embedded Office media when `--asset-dir` is supplied, and write `raw/assets/asset_context.json`.
- `scripts/create_asset_pages.py`: scan `raw/assets/` and create OKF-compatible `assets/asset-*.md` metadata page drafts with `# Source Context` when available.
- `scripts/validate_bundle.py`: fail the ingest if raw assets lack asset pages, embedded media lacks source context, or asset pages still contain TODO markers.
