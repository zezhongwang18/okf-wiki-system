---
type: Durable Answer
title: How should agents query the company Wiki?
description: Standard answer for how an agent should use MCP tools to query an OKF-compatible company Wiki bundle.
resource: bundle://company-wiki-intelligence/questions/how-should-agents-query-company-wiki
tags:
  - agent
  - mcp
  - query-workflow
timestamp: 2026-06-25T00:00:00+08:00
sources:
  - sources/source-company-wiki-system.md
---

# Answer

Agents should query the bundle through MCP tools rather than using model memory or directly guessing file paths.

Recommended flow:

1. Read the bundle status.
2. Read the root or directory index.
3. Search the bundle with several query variants for complex questions.
4. Read complete concept pages.
5. Follow links and related graph edges.
6. Retrieve relevant assets.
7. Use the company OCR/image skill if an image needs interpretation.
8. Answer with citations to concept, source, and asset pages.

# Citations

[1] [Source - Company Wiki System](../sources/source-company-wiki-system.md)
