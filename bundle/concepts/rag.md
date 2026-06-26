---
type: Concept
title: RAG
description: Retrieval-augmented generation, used here to locate relevant bundle pages rather than answer from isolated chunks.
resource: bundle://company-wiki-intelligence/concepts/rag
tags:
  - retrieval
  - search
  - agent
timestamp: 2026-06-25T00:00:00+08:00
sources:
  - sources/source-company-wiki-system.md
---

# Overview

RAG retrieves context for a model at question time.

In this system, RAG is page-location infrastructure. It should help the agent find relevant bundle pages, sections, related nodes, and assets. It should not force the agent to answer from isolated chunks alone.

# Weakness Addressed

Traditional raw-document RAG can lose context because arbitrary chunks separate claims from definitions, caveats, and diagrams. The OKF-compatible Wiki reduces this risk by indexing structured knowledge pages and then reading complete pages.

# Related Concepts

- [LLM Wiki](llm-wiki.md)
- [Progressive Disclosure](progressive-disclosure.md)

# Citations

[1] [Source - Company Wiki System](../sources/source-company-wiki-system.md)
