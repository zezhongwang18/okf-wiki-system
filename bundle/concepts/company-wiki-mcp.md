---
type: Concept
title: Company Wiki MCP
description: A read-only MCP server that exposes OKF-compatible bundle search, page reading, graph, and asset tools to company agents.
resource: mcp://company-wiki
tags:
  - mcp
  - tools
  - agent-access
timestamp: 2026-06-25T00:00:00+08:00
sources:
  - sources/source-company-wiki-system.md
---

# Overview

Company Wiki MCP is the tool layer between agents and the bundle.

The agent should not need to know file-system details. It calls tools such as `search_bundle`, `read_concept`, `get_related_links`, `get_page_assets`, and `read_asset_metadata`.

# Design Rules

- Read-only by default.
- No `ripgrep` dependency on employee machines.
- No local OCR dependency.
- Search locates pages; read tools return complete context.
- Asset tools return metadata and file paths so the company's OCR/image skill can process images if needed.

# Related Concepts

- [Company Wiki Reader Skill](company-wiki-reader-skill.md)
- [Image-Aware Knowledge Assets](image-aware-knowledge-assets.md)

# Citations

[1] [Source - Company Wiki System](../sources/source-company-wiki-system.md)
