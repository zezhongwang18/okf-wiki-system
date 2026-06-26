---
type: Source Summary
title: Source - Company Wiki System
description: Source summary for our existing Skill + MCP + LLM Wiki system design.
resource: file:///Users/jacksonwong/Documents/New%20project/company-wiki-system/docs/company-wiki-intelligence-system.md
tags:
  - company-wiki
  - mcp
  - skills
  - rag
timestamp: 2026-06-25T00:00:00+08:00
---

# Summary

The Company Wiki Intelligence System combines a builder skill, a reader skill, a Markdown Wiki, and a read-only MCP server.

# Useful Ideas

- Builder Skill creates and maintains the Wiki.
- Reader Skill tells agents when and how to query the Wiki.
- MCP exposes search, reading, graph, source, and asset tools.
- RAG should locate relevant pages instead of forcing answers from isolated chunks.
- Employee machines should not need `ripgrep`.
- Employee machines should not need local OCR.
- Image assets should be represented with metadata pages and returned to the agent when relevant.

# Use In This Bundle

This source provides the system design being reformatted into an OKF-compatible bundle.

# Citations

[1] [Company Wiki Intelligence System](file:///Users/jacksonwong/Documents/New%20project/company-wiki-system/docs/company-wiki-intelligence-system.md)
