---
type: Concept
title: Image-Aware Knowledge Assets
description: A pattern for making diagrams, screenshots, charts, and media searchable and usable by agents without requiring local OCR packages.
resource: bundle://company-wiki-intelligence/concepts/image-aware-knowledge-assets
tags:
  - assets
  - images
  - ocr
  - visual-context
timestamp: 2026-06-25T00:00:00+08:00
sources:
  - sources/source-company-wiki-system.md
---

# Overview

Images should be first-class knowledge assets. The image file lives in `raw/assets/`; its metadata lives in `assets/`.

The metadata page contains a title, description, `resource` path, MIME type, tags, and links to concepts it illustrates.

# OCR Policy

The bundle and MCP server do not require local OCR installation. If OCR or visual interpretation is needed, the agent uses the company's existing OCR/image skill on the `absolute_asset_path` returned by MCP.

# Example Asset

See [Asset - Wiki RAG Flow Diagram](../assets/asset-wiki-rag-flow.md).

# Citations

[1] [Source - Company Wiki System](../sources/source-company-wiki-system.md)
