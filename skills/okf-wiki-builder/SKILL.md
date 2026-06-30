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
7. Create durable answers under `questions/` for reusable questions the source can answer.
8. Link images at question level: question pages use `# Assets Used`, and asset pages use `# Applicable Questions`.
9. Create maps under `maps/` for navigation.
10. Use standard Markdown links for internal bundle references unless a target page does not exist yet.
11. Add `# Citations` to pages that make sourced claims.
12. Maintain `graph.yml` for typed relationships, including asset nodes and question-level asset relationships.
13. Regenerate directory-level `index.md` files for progressive disclosure.
14. Finalize the bundle with `scripts/finalize_bundle.py bundle`. This single required command generates mandatory exports and runs validation.
15. Confirm that `bundle/exports/upload/` contains Markdown files. If raster images exist, confirm that `bundle/exports/image-catalog.docx` and `bundle/exports/upload/image-catalog.docx` both exist.
16. Do not run separate export/validation commands as a substitute unless `finalize_bundle.py` is unavailable; if using the fallback, run the image catalog exporter when needed, then the upload exporter, then the validator.
17. Append to `log.md`.
18. Report completion only after validation passes.

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
4. every image/media file in `bundle/raw/assets/` has a matching `bundle/assets/asset-*.md` page;
5. image-heavy source summaries link to the relevant asset metadata pages.

If an Office file is known or expected to contain images but no assets are extracted, stop and report the extraction gap instead of silently continuing.

For standalone image files, copy them to `bundle/raw/assets/` first, then run `scripts/create_asset_pages.py` before answering or summarizing. A raw image without an asset metadata page is incomplete ingest.

When `bundle/raw/assets/` contains raster images, finalization must create:

```text
bundle/exports/image-catalog.docx
bundle/exports/upload/image-catalog.docx
```

The generated `bundle/exports/image-catalog.docx` is mandatory. It must embed image bodies directly in Word; a path-only catalog is incomplete.

## Upload Export Gate

OKF keeps directory indexes named `index.md`, but upload platforms may flatten paths and reject duplicate filenames.

Before reporting completion, always run:

```bash
python skills/okf-wiki-builder/scripts/finalize_bundle.py bundle
```

This creates `bundle/exports/upload/` with unique filenames and then validates the result:

```text
index.md              -> root-index.md
concepts/index.md     -> concepts-index.md
sources/index.md      -> sources-index.md
assets/index.md       -> assets-index.md
concepts/rag.md       -> concepts-rag.md
```

Upload `bundle/exports/upload/` to platforms that do not preserve folder paths. Do not upload raw OKF directories directly to such platforms.

## Completion Gate

Do not say ingest is complete while generated pages still contain `TODO`, `Source Page TODO`, `Concept TODO`, or `Context unavailable`.

Before reporting completion, run the finalizer:

```bash
python skills/okf-wiki-builder/scripts/finalize_bundle.py bundle
```

When finalization or validation fails, report the failed checks and continue fixing them. Do not summarize a failed ingest as complete.

Validation fails when raster image assets exist but `bundle/exports/image-catalog.docx` is missing or does not contain embedded `word/media/*` image bodies. Validation also fails when `bundle/exports/upload/` is missing, incomplete, or would contain duplicate Markdown filenames.

Validation also fails when source, concept, question, or asset pages are missing the required detail-preservation sections below.

Validation also fails when assets are not bound at question level. Source context explains where an image came from; it does not make the image applicable to every question from the same source.

## Detail Preservation Rules

Do not create summary-only pages. Preserve answerable detail in structured sections so vector search can retrieve more than a short abstract.

Every `Source Summary` page must include:

```text
# Summary
# Key Facts
# Procedures Or Workflows
# Rules And Exceptions
# Terms, Fields, Metrics, Or Parameters
# Evidence Snippets
# Questions This Source Can Answer
# Details Not Fully Extracted
# Citations
```

Rules:

- `# Key Facts` must preserve concrete facts, dates, names, thresholds, requirements, and decisions.
- `# Procedures Or Workflows` must preserve ordered steps when the source contains processes.
- `# Rules And Exceptions` must preserve constraints, exceptions, eligibility rules, and failure cases.
- `# Terms, Fields, Metrics, Or Parameters` must preserve table fields, sheet names, units, formulas, enums, and configuration values when present.
- `# Evidence Snippets` must preserve short source-grounded excerpts or close paraphrases for important claims.
- `# Questions This Source Can Answer` must list reusable user questions this source can answer.
- `# Details Not Fully Extracted` must explicitly say what still requires raw-source review; write `None identified.` only after checking.

Every `Concept` page must include:

```text
# Overview
# Detailed Notes
# When To Use
# Rules And Exceptions
# Examples
# Related Sources
# Citations
```

Every `Durable Answer` / question page must include:

```text
# Answer
# Assets Used
# Evidence
# Caveats
# Related
# Citations
```

Use `# Assets Used` to explicitly list image assets needed for this answer:

```md
# Assets Used

- [MCP configuration screenshot](../assets/asset-mcp-config.md)
```

If no image is needed, write:

```md
# Assets Used

None.
```

Every `Image Asset` page must include:

```text
# Description
# Applicable Questions
# Not Applicable To
# Source Context
# Visible Text
# Visual Notes
# Related
# Citations
```

Rules:

- `# Applicable Questions` decides when an image can appear in an answer.
- `# Source Context` must not be used as the reason to automatically show the image.
- If applicability is unknown, write `Not assigned.`. Such an image can remain in the catalog but must not be auto-attached to answers.
- When a question page lists an asset in `# Assets Used`, the asset page must list the question title or path in `# Applicable Questions`.

If a section is not applicable, write `Not applicable.` with a brief reason. Do not leave required sections empty. Do not use TODO markers in completed output.

## Image Context Binding Rule

Asset descriptions must be grounded in source context. Do not describe an extracted image only from the file name or the whole document topic.

For authoring source documents, prefer this layout:

```text
Relevant body paragraphs
Figure title or caption
Image
```

During ingest, bind each image to the nearest preceding heading and the body text in that same heading section before the image. Also capture the nearest caption and recent preceding paragraphs. Treat following text as context only when it clearly looks like a caption. This avoids binding an image to an unrelated next section while preserving more than a single preceding paragraph.

The bundled extractor writes `bundle/raw/assets/asset_context.json` for Office sources. For DOCX, it records `section_paragraphs_before` for same-heading context and `recent_paragraphs_before` for the local window. The asset page generator reads it and writes a `# Source Context` section into each `assets/asset-*.md` page.

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
5. If OCR/image inspection is unavailable, state that visual interpretation has not been performed and write `OCR unavailable.` or `Visual inspection unavailable.` in the relevant section. Do not use TODO markers in completed output.

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
- `scripts/export_image_catalog_docx.py`: create mandatory `exports/image-catalog.docx` with image titles, context, OCR text, and embedded image bodies for platforms that only accept Word files.
- `scripts/export_upload_package.py`: create mandatory `exports/upload/` with upload-safe unique filenames so `index.md` files do not collide on platforms that flatten paths.
- `scripts/validate_bundle.py`: fail the ingest if raw assets lack asset pages, embedded media lacks source context, or asset pages still contain TODO markers.
