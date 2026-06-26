---
type: Concept
title: OKF-Compatible LLM Wiki Bundle
description: A portable Markdown knowledge bundle that follows OKF conventions while preserving LLM Wiki source summaries, assets, questions, and graph extensions.
resource: bundle://company-wiki-intelligence/concepts/okf-compatible-llm-wiki-bundle
tags:
  - okf
  - llm-wiki
  - knowledge-bundle
timestamp: 2026-06-25T00:00:00+08:00
sources:
  - sources/source-google-okf.md
  - sources/source-company-wiki-system.md
---

# Overview

An OKF-compatible LLM Wiki Bundle stores company knowledge as Markdown files with YAML frontmatter. It can be read by people, indexed by search systems, and queried by agents.

The bundle follows OKF's core rules:

- Every concept is a Markdown file.
- Frontmatter includes `type`, `title`, `description`, `resource`, `tags`, and `timestamp`.
- `index.md` files provide progressive disclosure.
- Links use standard Markdown paths where possible.
- Claims are backed by `# Citations`.

# LLM Wiki Extensions

This bundle extends OKF with conventions that are useful for agent work:

- `raw/` preserves immutable source files and asset files.
- `sources/` stores source summaries.
- `questions/` stores durable answers.
- `assets/` stores image and media metadata pages.
- `graph.yml` stores typed relationships between concepts, sources, questions, and assets.
- MCP exposes the bundle as query tools.

# Relationship To RAG

RAG is not the source of truth. It is the retrieval layer that helps an agent locate which bundle pages to read. The answer should be grounded in complete pages, source summaries, and assets where relevant.

# Citations

[1] [Source - Google Open Knowledge Format](../sources/source-google-okf.md)
[2] [Source - Company Wiki System](../sources/source-company-wiki-system.md)
