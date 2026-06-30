#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from zipfile import ZipFile
from pathlib import Path


MEDIA_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".svg", ".heic",
    ".mp4", ".mov", ".mp3", ".wav", ".m4a", ".pdf",
}

WORD_EMBEDDABLE_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp"}


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


def embedded_word_media_count(docx_path: Path) -> int:
    try:
        with ZipFile(docx_path) as archive:
            return len([
                name for name in archive.namelist()
                if name.startswith("word/media/") and not name.endswith("/")
            ])
    except Exception:
        return 0


def upload_export_name(bundle: Path, source: Path) -> str:
    rel = source.relative_to(bundle)
    parts = list(rel.parts)
    if parts == ["index.md"]:
        return "root-index.md"
    def slug(value: str) -> str:
        value = value.lower()
        value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
        value = re.sub(r"-{2,}", "-", value).strip("-")
        return value or "page"
    stem = Path(parts[-1]).stem
    if stem == "index":
        stem = f"{'-'.join(slug(part) for part in parts[:-1])}-index"
    else:
        stem = "-".join([*(slug(part) for part in parts[:-1]), slug(stem)])
    return f"{stem}.md"


def upload_source_pages(bundle: Path) -> list[Path]:
    pages: list[Path] = []
    for path in sorted(bundle.rglob("*.md")):
        rel_parts = path.relative_to(bundle).parts
        if not rel_parts or rel_parts[0] in {"raw", "exports"}:
            continue
        if any(part.startswith(".") for part in rel_parts):
            continue
        pages.append(path)
    return pages


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

    embeddable_images = [
        path for path in media_files
        if path.suffix.lower() in WORD_EMBEDDABLE_IMAGE_SUFFIXES
    ]
    if embeddable_images:
        catalog = bundle / "exports" / "image-catalog.docx"
        if not catalog.exists():
            errors.append("Image assets exist but exports/image-catalog.docx is missing.")
        else:
            embedded_count = embedded_word_media_count(catalog)
            if embedded_count < len(embeddable_images):
                errors.append(
                    "exports/image-catalog.docx does not embed all raster image bodies "
                    f"({embedded_count} embedded media file(s), {len(embeddable_images)} raster image asset(s))."
                )

    upload_sources = upload_source_pages(bundle)
    upload_dir = bundle / "exports" / "upload"
    if upload_sources:
        if not upload_dir.exists():
            errors.append("Uploadable Markdown pages exist but exports/upload/ is missing.")
        else:
            expected_names = [upload_export_name(bundle, page) for page in upload_sources]
            duplicate_expected = sorted({name for name in expected_names if expected_names.count(name) > 1})
            for name in duplicate_expected:
                errors.append(f"Upload export filename collision would occur: {name}")
            exported_md = sorted(path.name for path in upload_dir.glob("*.md"))
            duplicate_exported = sorted({name for name in exported_md if exported_md.count(name) > 1})
            for name in duplicate_exported:
                errors.append(f"Duplicate filename in exports/upload/: {name}")
            for name in expected_names:
                if not (upload_dir / name).exists():
                    errors.append(f"Missing upload-safe export file: exports/upload/{name}")
            if len(set(exported_md)) != len(exported_md):
                errors.append("exports/upload/ contains duplicate Markdown basenames.")
            if embeddable_images and not (upload_dir / "image-catalog.docx").exists():
                errors.append("Raster image assets exist but exports/upload/image-catalog.docx is missing.")

    for warning in warnings:
        print(f"WARN: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)

    print(f"OKF bundle validation passed: {bundle}")
    print(f"Checked {len(media_files)} raw asset(s) and {len(resources)} asset page(s).")
    if embeddable_images:
        print(f"Checked mandatory image catalog: exports/image-catalog.docx")
    if upload_sources:
        print(f"Checked mandatory upload export: exports/upload/")


if __name__ == "__main__":
    main()
