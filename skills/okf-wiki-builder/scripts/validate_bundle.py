#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


MEDIA_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".svg", ".heic",
    ".mp4", ".mov", ".mp3", ".wav", ".m4a", ".pdf",
}


def read_resource(page: Path) -> str | None:
    text = page.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"^resource:\s*(.+)$", text, re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip().strip("\"'")


def has_todo(page: Path) -> bool:
    text = page.read_text(encoding="utf-8", errors="replace")
    return bool(re.search(r"\bTODO\b|Source Page TODO|Concept TODO|Context unavailable", text, re.I))


def display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate OKF bundle ingest completeness.")
    parser.add_argument("bundle", nargs="?", default=".", help="OKF bundle root")
    parser.add_argument("--allow-drafts", action="store_true", help="Allow TODO markers in asset pages")
    args = parser.parse_args()

    bundle = Path(args.bundle).resolve()
    raw_assets = bundle / "raw" / "assets"
    asset_pages = bundle / "assets"
    errors: list[str] = []
    warnings: list[str] = []

    for required in [bundle / "index.md", bundle / "log.md", asset_pages, raw_assets]:
        if not required.exists():
            errors.append(f"Missing required path: {display_path(required, bundle)}")

    resources: dict[str, Path] = {}
    if asset_pages.exists():
        for page in asset_pages.glob("*.md"):
            if page.name == "index.md":
                continue
            resource = read_resource(page)
            if not resource:
                errors.append(f"Asset page missing resource frontmatter: {page.relative_to(bundle)}")
                continue
            resources[resource] = page
            if has_todo(page):
                message = f"Asset page still contains TODO or unavailable context: {page.relative_to(bundle)}"
                if args.allow_drafts:
                    warnings.append(message)
                else:
                    errors.append(message)

    media_files = []
    if raw_assets.exists():
        media_files = [
            path for path in raw_assets.rglob("*")
            if path.is_file() and path.suffix.lower() in MEDIA_SUFFIXES
        ]
        for media in media_files:
            resource = media.relative_to(bundle).as_posix()
            if resource not in resources:
                errors.append(f"Raw asset has no matching asset page resource: {resource}")

    embedded_media = [path for path in media_files if "-embedded-" in path.name]
    if embedded_media and not (raw_assets / "asset_context.json").exists():
        errors.append("Embedded Office media exists but raw/assets/asset_context.json is missing.")

    if embedded_media:
        context_text = (raw_assets / "asset_context.json").read_text(encoding="utf-8", errors="replace") if (raw_assets / "asset_context.json").exists() else ""
        for media in embedded_media:
            if media.name not in context_text:
                errors.append(f"Embedded asset missing from asset_context.json: {media.name}")

    for warning in warnings:
        print(f"WARN: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)

    print(f"OKF bundle validation passed: {bundle}")
    print(f"Checked {len(media_files)} raw asset(s) and {len(resources)} asset page(s).")


if __name__ == "__main__":
    main()
