#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import shutil
from pathlib import Path


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "page"


def iter_upload_sources(bundle: Path) -> list[Path]:
    sources: list[Path] = []
    for path in sorted(bundle.rglob("*.md")):
        rel_parts = path.relative_to(bundle).parts
        if not rel_parts:
            continue
        if rel_parts[0] in {"raw", "exports"}:
            continue
        if any(part.startswith(".") for part in rel_parts):
            continue
        sources.append(path)
    return sources


def export_name(bundle: Path, source: Path) -> str:
    rel = source.relative_to(bundle)
    parts = list(rel.parts)
    if parts == ["index.md"]:
        return "root-index.md"
    stem = Path(parts[-1]).stem
    if stem == "index":
        stem = f"{'-'.join(slugify(part) for part in parts[:-1])}-index"
    else:
        stem = "-".join([*(slugify(part) for part in parts[:-1]), slugify(stem)])
    return f"{stem}.md"


def export_markdown(bundle: Path, output_dir: Path, clean: bool) -> int:
    if clean and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    used: dict[str, Path] = {}
    count = 0
    for source in iter_upload_sources(bundle):
        name = export_name(bundle, source)
        if name in used:
            raise SystemExit(f"Export name collision: {source.relative_to(bundle)} and {used[name].relative_to(bundle)} -> {name}")
        used[name] = source
        rel = source.relative_to(bundle).as_posix()
        text = source.read_text(encoding="utf-8", errors="replace")
        banner = f"<!-- OKF upload export. Original path: {rel} -->\n\n"
        (output_dir / name).write_text(banner + text, encoding="utf-8")
        count += 1
    return count


def copy_image_catalog(bundle: Path, output_dir: Path) -> bool:
    catalog = bundle / "exports" / "image-catalog.docx"
    if not catalog.exists():
        return False
    output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(catalog, output_dir / "image-catalog.docx")
    return True


def main() -> None:
    if os.environ.get("OKF_FINALIZE_RUNNING") != "1":
        raise SystemExit(
            "Do not run export_upload_package.py directly as a completion step. "
            "Run finalize_bundle.py so upload export, image catalog export, and validation happen together."
        )
    parser = argparse.ArgumentParser(description="Export OKF bundle pages to upload-safe unique filenames.")
    parser.add_argument("bundle", nargs="?", default=".", help="OKF bundle root")
    parser.add_argument("--output-dir", help="Output directory; defaults to bundle/exports/upload")
    parser.add_argument("--no-clean", action="store_true", help="Do not clear the output directory before export")
    args = parser.parse_args()

    bundle = Path(args.bundle).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else bundle / "exports" / "upload"
    count = export_markdown(bundle, output_dir, clean=not args.no_clean)
    copied_catalog = copy_image_catalog(bundle, output_dir)
    print(f"Wrote {count} upload-safe Markdown file(s) to {output_dir}.")
    if copied_catalog:
        print("Copied image-catalog.docx into the upload package.")


if __name__ == "__main__":
    main()
