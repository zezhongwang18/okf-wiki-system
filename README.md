# Google OKF-Compatible LLM Wiki Bundle

This package is a fresh OKF-compatible version of the Company Wiki Intelligence System.

It does not modify the existing `company-wiki-system`. It re-expresses the same ideas using the Open Knowledge Format style:

```text
Markdown files
+ YAML frontmatter
+ directory indexes
+ standard Markdown links
+ citations
+ MCP tools
+ Agent skills
```

## Contents

```text
bundle/
  OKF-compatible sample knowledge bundle.

skills/
  okf-wiki-builder/
  okf-wiki-reader/

mcp-server/
  Read-only MCP server for OKF-compatible bundles.

docs/
  Architecture, conventions, and migration guidance.

examples/
  Windows and local MCP configuration examples.
```

## Design Position

This is best described as:

```text
OKF-compatible LLM Wiki Bundle
```

It follows Google OKF's core conventions:

- Bundle as a directory.
- Concepts as Markdown files.
- YAML frontmatter.
- `index.md` for progressive disclosure.
- `log.md` for history.
- Standard Markdown links for relationships.
- `# Citations` for evidence.

It extends OKF with:

- `raw/` source and asset preservation.
- `graph.yml` typed relationship graph.
- `questions/` durable answer pages.
- `assets/` image/media metadata pages.
- MCP tools for agent consumption.
- Skills for building and querying.

## Quick Test

```bash
cd "/Users/jacksonwong/Documents/New project/google-okf-boundle/mcp-server"
OKF_BUNDLE_ROOT="/Users/jacksonwong/Documents/New project/google-okf-boundle/bundle" node src/inspect.js "LLM Wiki RAG MCP"
```

No `ripgrep` / `rg` is required. No local OCR package is required.

## Image-Aware Workflow

The OKF builder does not treat images as invisible attachments.

When source files contain screenshots, charts, diagrams, or Office-embedded media, the builder should:

1. preserve binary files under `bundle/raw/assets/`;
2. create searchable Markdown metadata pages under `bundle/assets/`;
3. let the company Agent OCR/image skill fill in visible text and visual notes when needed;
4. expose the metadata page and original file path through MCP.

This keeps the company computer lightweight: no `rg`, no `grep`, and no local OCR installation are required for normal use.

See `docs/asset-workflow.md` for the detailed flow.
