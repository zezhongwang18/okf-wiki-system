# Migration From Current Company Wiki System

Do not overwrite the existing system. Migrate by generating a new OKF-compatible bundle.

## Field Mapping

Current frontmatter:

```yaml
type: concept
title: LLM Wiki
created: 2026-06-25
updated: 2026-06-25
sources: []
tags: []
```

OKF-compatible frontmatter:

```yaml
type: Concept
title: LLM Wiki
description: Maintained Markdown knowledge layer over raw sources.
resource: bundle://company-wiki/concepts/llm-wiki
tags:
  - wiki
timestamp: 2026-06-25T00:00:00+08:00
sources: []
```

## Directory Mapping

```text
wiki/concepts/   -> bundle/concepts/
wiki/sources/    -> bundle/sources/
wiki/entities/   -> bundle/concepts/ or bundle/entities/ if retained
wiki/questions/  -> bundle/questions/
wiki/maps/       -> bundle/maps/
raw/assets/      -> bundle/raw/assets/
wiki/graph.yml   -> bundle/graph.yml
```

## Link Mapping

Prefer standard Markdown links:

```md
[RAG](rag.md)
[Source - Company Wiki System](../sources/source-company-wiki-system.md)
```

If old pages use `[[RAG]]`, convert them during migration or have the MCP parser support both.

## Index Mapping

Create indexes at each level:

```text
bundle/index.md
bundle/concepts/index.md
bundle/sources/index.md
bundle/assets/index.md
bundle/questions/index.md
bundle/maps/index.md
```

## Recommended Migration Steps

1. Copy existing source summaries into `bundle/sources/`.
2. Convert concept pages into OKF frontmatter.
3. Convert `[[Wiki Links]]` into Markdown links when path is known.
4. Create asset metadata pages for images.
5. Preserve raw files under `bundle/raw/`.
6. Convert or preserve `graph.yml` as a typed OKF extension.
7. Generate directory indexes.
8. Run MCP inspection against the new bundle.
9. Configure the company Agent with `okf-wiki-reader`.

## Asset Migration Steps

For images and Office-embedded media:

1. Put original binary assets under `bundle/raw/assets/`.
2. Run `okf-wiki-builder/scripts/create_asset_pages.py` to create `bundle/assets/asset-*.md` pages.
3. Link each asset page to the source summary that produced it.
4. Use the company Agent OCR/image skill to fill `# Visible Text` and `# Visual Notes` when the asset contains important text or visual evidence.
5. Add graph edges such as `extracted_from`, `illustrates`, or `supports` when the relationship is clear.

If migrating from the previous `llm-wiki-builder`, keep its raw files unchanged and generate the OKF bundle as a new output. Do not overwrite the previous wiki.
