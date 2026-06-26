# OKF-Compatible LLM Wiki Architecture

## Design Goal

This package turns our previous Company Wiki Intelligence System into an OKF-compatible form.

The target description is:

```text
An OKF-compatible LLM Wiki Bundle served to agents through MCP and governed by builder/reader skills.
```

## Layers

```text
Raw materials
        |
        v
okf-wiki-builder skill
        |
        v
OKF-compatible bundle
  Markdown + frontmatter
  directory indexes
  source summaries
  asset metadata
  durable questions
  typed graph extension
        |
        v
okf-wiki-mcp
        |
        v
okf-wiki-reader skill
        |
        v
Company Agent
```

## Borrowed From Google OKF

- Bundle as a directory.
- Concept as one Markdown document.
- YAML frontmatter.
- `type`, `title`, `description`, `resource`, `tags`, `timestamp`.
- `index.md` for progressive disclosure.
- `log.md` for history.
- Standard Markdown links.
- `# Citations` for evidence.
- Permissive consumption of unknown fields.

## Our Extensions

- `raw/` for immutable sources and assets.
- `sources/` for source summaries.
- `questions/` for durable answers.
- `assets/` for image/media metadata.
- `graph.yml` for typed relationships.
- MCP tools for serving the bundle to agents.
- Skills for construction and query behavior.

## Why This Is Better Than The Previous Internal Format

The previous format works, but it is more custom. This OKF-compatible version adds:

- Better interoperability with Markdown tools.
- More consistent frontmatter.
- Directory-level progressive disclosure.
- Standard Markdown links.
- Clear distinction between bundle format, MCP serving, and agent behavior.
- A stronger story for IT and governance because it aligns with an open, vendor-neutral format.

## OCR and Images

Images are represented as asset metadata pages.

The MCP server returns paths. It does not perform OCR locally.

If OCR or visual interpretation is needed, the agent calls the company's OCR/image skill using the returned path.

The builder preserves Office-embedded media from common internal package folders:

- `.docx`: `word/media/`
- `.pptx`: `ppt/media/`
- `.xlsx` / `.xlsm`: `xl/media/`

Those files are copied into `bundle/raw/assets/`, then `okf-wiki-builder/scripts/create_asset_pages.py` creates `bundle/assets/asset-*.md` pages. The metadata pages make images discoverable through ordinary text search before OCR is available.

## No ripgrep Requirement

The MCP server searches with Node.js. Employee machines do not need `ripgrep` / `rg`.

For production scale, search can be replaced behind the MCP interface with SQLite FTS, OpenSearch, pgvector, Qdrant, or another index.

This matters for locked-down Windows machines: the Agent only needs a configured MCP server, not extra command-line search tools.
