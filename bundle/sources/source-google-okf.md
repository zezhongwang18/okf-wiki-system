---
type: Source Summary
title: Source - Google Open Knowledge Format
description: Source summary for Google Knowledge Catalog OKF conventions that inform this bundle.
resource: file:///Users/jacksonwong/Downloads/knowledge-catalog-main/okf/SPEC.md
tags:
  - okf
  - google
  - markdown
  - frontmatter
timestamp: 2026-06-25T00:00:00+08:00
---

# Summary

Open Knowledge Format defines a vendor-neutral way to represent knowledge as Markdown files with YAML frontmatter.

# Useful Ideas

- A knowledge corpus should be a portable bundle.
- Each concept is a Markdown document.
- Frontmatter should include at least `type`; recommended fields include `title`, `description`, `resource`, `tags`, and `timestamp`.
- `index.md` files support progressive disclosure.
- `log.md` files record update history.
- Standard Markdown links express relationships.
- `# Citations` records provenance.
- Consumers should tolerate unknown fields and partial bundles.

# Use In This Bundle

This bundle adopts OKF-compatible frontmatter and directory indexes, while adding LLM Wiki extensions for sources, assets, questions, graph relationships, and MCP access.

# Citations

[1] [OKF SPEC](file:///Users/jacksonwong/Downloads/knowledge-catalog-main/okf/SPEC.md)
