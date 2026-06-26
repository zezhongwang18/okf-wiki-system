# Image and Asset Workflow

This workflow makes images searchable without requiring local OCR or extra command-line search tools on company Windows computers.

## Problem

Images are hard for keyword search because the useful knowledge is inside the pixels, not in the filename.

The OKF bundle solves this by creating a Markdown asset page for each important image or media file.

## Storage Model

```text
bundle/
  raw/
    assets/
      architecture-diagram.png
  assets/
    asset-architecture-diagram.md
```

`raw/assets/` stores the original file.

`assets/asset-*.md` stores searchable metadata, OCR text, visual notes, source links, and concept links.

## Builder Flow

1. Preserve source documents under `bundle/raw/sources/`.
2. Extract text when useful.
3. For Office documents, preserve embedded media with:

```bash
python skills/okf-wiki-builder/scripts/extract_source_text.py source.docx extracted.txt --asset-dir bundle/raw/assets
```

4. Create asset metadata pages with:

```bash
python skills/okf-wiki-builder/scripts/create_asset_pages.py bundle --source-page sources/source-example.md
```

5. Review the generated `# Source Context` section before writing image descriptions.
6. Replace TODO fields with descriptions grounded in source context.
7. If the company Agent has an OCR/image skill, use it to fill `# Visible Text` and `# Visual Notes`.
8. Link the asset page to related concepts and source summaries.
9. Run validation before reporting completion:

```bash
python skills/okf-wiki-builder/scripts/validate_bundle.py bundle
```

## Office Embedded Media

The extractor preserves common embedded media folders:

- `.docx`: `word/media/`
- `.pptx`: `ppt/media/`
- `.xlsx` / `.xlsm`: `xl/media/`

This means diagrams and screenshots inside Office files are not lost during wiki creation.

## Source Context Binding

The extractor writes `raw/assets/asset_context.json` for Office-embedded media.

The asset page generator reads that file and adds `# Source Context` to asset pages. This section records the nearest source location, such as:

- DOCX nearest heading, caption, same-heading text before the image, recent previous paragraphs, and image paragraph
- PPTX slide number, slide title, and slide text
- XLSX workbook-level extraction note when exact sheet/cell anchoring is unavailable

Company document authors must place images after the relevant body text when they want automatic source-context binding:

```text
Relevant explanation
Figure title or caption
Image
```

The ingest rule prioritizes same-heading text before the image plus nearby captions. Following text is used only when it clearly looks like a caption, so an unrelated next section is less likely to be bound to the image.

## Completion Gate

An ingest pass is not complete when:

- a raw image/media file has no matching `assets/asset-*.md` page
- embedded Office media exists but `raw/assets/asset_context.json` is missing
- an embedded asset is not listed in `asset_context.json`
- an asset page still contains unresolved TODO markers

Use `--allow-drafts` only when the user explicitly asks for draft output.

## Reader Flow

When a user asks a question that mentions or implies images, the Agent must:

1. call `search_bundle` for normal concept/source pages;
2. call `search_assets` for diagrams, screenshots, charts, UI images, or figures;
3. call `read_asset_metadata` for likely assets;
4. call the company OCR/image skill on the returned asset path when visual understanding is needed;
5. answer with citations to the asset page and related source/concept pages.

## Why MCP Does Not OCR

The MCP server stays lightweight and read-only.

It returns file paths and metadata. OCR is delegated to the company Agent because that capability already exists there and may be governed by company security controls.

## Windows Constraint

The OKF MCP server searches with Node.js code. It does not call `rg`, `grep`, or other shell search utilities.

This avoids installing extra command-line tools on locked-down Windows machines.
