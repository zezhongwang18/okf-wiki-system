---
type: Concept
title: Company Wiki Reader Skill
description: Agent behavior rules that require company knowledge questions to be answered through the OKF-compatible bundle and MCP tools.
resource: skill://okf-wiki-reader
tags:
  - skill
  - agent
  - query-workflow
timestamp: 2026-06-25T00:00:00+08:00
sources:
  - sources/source-company-wiki-system.md
---

# Overview

The reader skill tells an agent when to query the company bundle and how to use the MCP tools.

# Query Pattern

1. Get bundle status.
2. Read the root or directory index.
3. Generate multiple search queries for complex questions.
4. Search the bundle.
5. Read complete concepts.
6. Follow links and graph relationships.
7. Retrieve related assets.
8. Use the company OCR/image skill if visual interpretation is needed.
9. Answer with citations.

# Citations

[1] [Source - Company Wiki System](../sources/source-company-wiki-system.md)
