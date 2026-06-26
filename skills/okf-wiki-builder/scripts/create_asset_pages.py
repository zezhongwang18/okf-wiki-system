#!/usr/bin/env python3
from __future__ import annotations

import argparse
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


def image_size(path: Path) -> Optional[str]:
    try:
        from PIL import Image  # type: ignore

        with Image.open(path) as image:
            return f"{image.width} x {image.height}"
    except Exception:
        return None


def make_page(bundle: Path, asset: Path, source: str | None, ts: str) -> str:
    resource = asset.relative_to(bundle).as_posix()
    mime_type = mimetypes.guess_type(asset.name)[0] or "application/octet-stream"
    title = asset.stem.replace("-", " ").replace("_", " ").strip().title()
    size = image_size(asset)
    sources = f"\n  - {source}" if source else " []"
    size_line = f"\n- Size: {size}" if size else ""

    return f"""---
type: Image Asset
title: {title}
description: Metadata page for `{asset.name}`. Replace this with a specific description after visual review.
resource: {resource}
mime_type: {mime_type}
tags: []
timestamp: {ts}
sources:{sources}
---

# Description

TODO: Describe what this asset shows and why it matters.

# File Metadata

- Resource: `{resource}`
- MIME type: `{mime_type}`{size_line}

# Visible Text

TODO: Use the company's OCR/image skill if the asset contains text.

# Visual Notes

TODO: Use the company's OCR/image skill or manual review to describe diagrams, screenshots, charts, UI states, or other visual evidence.

# Related

- Extracted from: [Source Page TODO](../sources/source-todo.md)
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
        page.write_text(make_page(bundle, asset, args.source_page, ts), encoding="utf-8")
        written += 1

    print(f"Wrote {written} OKF asset page(s), skipped {skipped} existing asset(s).")


if __name__ == "__main__":
    main()
