#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import mimetypes
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".svg", ".heic"}
MEDIA_SUFFIXES = IMAGE_SUFFIXES | {".mp4", ".mov", ".mp3", ".wav", ".m4a", ".pdf"}


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "asset"


def timestamp() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_existing_resources(asset_dir: Path) -> set[str]:
    resources: set[str] = set()
    if not asset_dir.exists():
        return resources
    for page in asset_dir.glob("*.md"):
        text = page.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"^resource:\s*(.+)$", text, re.MULTILINE)
        if match:
            resources.add(match.group(1).strip().strip("\"'"))
    return resources


def load_asset_contexts(raw_assets: Path) -> dict[str, dict]:
    context_path = raw_assets / "asset_context.json"
    if not context_path.exists():
        return {}
    try:
        data = json.loads(context_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(data, list):
        return {}
    contexts: dict[str, dict] = {}
    for item in data:
        if isinstance(item, dict) and item.get("copied_asset"):
            contexts[str(item["copied_asset"])] = item
    return contexts


def image_size(path: Path) -> Optional[str]:
    try:
        from PIL import Image  # type: ignore

        with Image.open(path) as image:
            return f"{image.width} x {image.height}"
    except Exception:
        return None


def format_list(values: list[str], empty: str = "Not captured.") -> str:
    cleaned = [value.strip() for value in values if isinstance(value, str) and value.strip()]
    if not cleaned:
        return empty
    return "\n".join(f"- {value}" for value in cleaned)


def make_source_context(context: dict | None) -> str:
    if not context:
        return """# Source Context

Context unavailable. Do not infer the image meaning from the whole source alone; use OCR/image inspection or manual review before final interpretation.
"""

    location = context.get("source_location") if isinstance(context.get("source_location"), dict) else {}
    source_type = context.get("source_type", "unknown")
    confidence = context.get("binding_confidence", "unknown")
    source_file = context.get("source_file", "unknown")
    internal_path = context.get("internal_path", "unknown")
    rule = location.get("primary_context_rule", "Use the captured source location as the binding context.")

    lines = [
        "# Source Context",
        "",
        f"- Source file: `{source_file}`",
        f"- Source type: `{source_type}`",
        f"- Internal asset path: `{internal_path}`",
        f"- Binding confidence: `{confidence}`",
        f"- Binding rule: {rule}",
        "",
    ]

    if source_type == "docx":
        section_before = location.get("section_paragraphs_before")
        if not isinstance(section_before, list):
            section_before = location.get("paragraphs_before", [])
        recent_before = location.get("recent_paragraphs_before")
        if not isinstance(recent_before, list):
            recent_before = location.get("paragraphs_before", [])
        lines.extend([
            f"- Nearest heading: {location.get('nearest_heading') or 'Not captured.'}",
            f"- Heading paragraph index: {location.get('heading_paragraph_index') or 'Not captured.'}",
            f"- Paragraph index: {location.get('paragraph_index') or 'Not captured.'}",
            f"- Caption: {location.get('caption') or location.get('caption_after') or 'Not captured.'}",
            "",
            "## Same-Heading Text Before Image",
            "",
            format_list(section_before),
            "",
            "## Recent Text Before Image",
            "",
            format_list(recent_before),
            "",
            "## Image Paragraph Text",
            "",
            location.get("image_paragraph_text") or "Not captured.",
            "",
        ])
    elif source_type == "pptx":
        lines.extend([
            f"- Slide: {location.get('slide') or 'Not captured.'}",
            f"- Slide title: {location.get('slide_title') or 'Not captured.'}",
            "",
            "## Slide Text",
            "",
            format_list(location.get("slide_text", [])),
            "",
        ])
    else:
        lines.extend([
            "## Location Notes",
            "",
            location.get("primary_context_rule") or "Precise location was not captured.",
            "",
        ])

    return "\n".join(lines).rstrip() + "\n"


def make_page(bundle: Path, asset: Path, source: str | None, ts: str, context: dict | None) -> str:
    resource = asset.relative_to(bundle).as_posix()
    mime_type = mimetypes.guess_type(asset.name)[0] or "application/octet-stream"
    title = asset.stem.replace("-", " ").replace("_", " ").strip().title()
    size = image_size(asset)
    sources = f"\n  - {source}" if source else " []"
    size_line = f"\n- Size: {size}" if size else ""
    context_section = make_source_context(context)
    related_source = source or "sources/source-todo.md"

    return f"""---
type: Image Asset
title: {title}
description: Metadata page for `{asset.name}`. Replace this with a specific description after visual review.
resource: {resource}
mime_type: {mime_type}
source_context_available: {str(bool(context)).lower()}
tags: []
timestamp: {ts}
sources:{sources}
---

# Description

TODO: Describe what this asset shows and why it matters.

# Applicable Questions

Not assigned.

# Not Applicable To

Not assigned.

# File Metadata

- Resource: `{resource}`
- MIME type: `{mime_type}`{size_line}

{context_section}

# Visible Text

TODO: Use the company's OCR/image skill if the asset contains text.

# Visual Notes

TODO: Use the company's OCR/image skill or manual review to describe diagrams, screenshots, charts, UI states, or other visual evidence.

# Related

- Extracted from: [{related_source}](../{related_source})
- Illustrates: [Concept TODO](../concepts/concept-todo.md)

# Citations

"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Create OKF-compatible asset metadata pages for bundle/raw/assets.")
    parser.add_argument("bundle", nargs="?", default=".", help="OKF bundle root")
    parser.add_argument("--source-page", help="Optional source summary path to include in frontmatter sources")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing asset pages")
    args = parser.parse_args()

    bundle = Path(args.bundle).resolve()
    raw_assets = bundle / "raw" / "assets"
    asset_pages = bundle / "assets"
    asset_pages.mkdir(parents=True, exist_ok=True)

    if not raw_assets.exists():
        raise SystemExit(f"Missing raw assets directory: {raw_assets}")

    existing = set() if args.overwrite else read_existing_resources(asset_pages)
    contexts = load_asset_contexts(raw_assets)
    ts = timestamp()
    written = 0
    skipped = 0

    for asset in sorted(path for path in raw_assets.rglob("*") if path.is_file() and path.suffix.lower() in MEDIA_SUFFIXES):
        resource = asset.relative_to(bundle).as_posix()
        if resource in existing:
            skipped += 1
            continue

        stem = slugify(asset.stem)
        page = asset_pages / f"asset-{stem}.md"
        if page.exists() and not args.overwrite:
            counter = 2
            while True:
                candidate = asset_pages / f"asset-{stem}-{counter}.md"
                if not candidate.exists():
                    page = candidate
                    break
                counter += 1
        page.write_text(make_page(bundle, asset, args.source_page, ts, contexts.get(asset.name)), encoding="utf-8")
        written += 1

    print(f"Wrote {written} OKF asset page(s), skipped {skipped} existing asset(s).")


if __name__ == "__main__":
    main()
