#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import os
import sys
from zipfile import ZipFile
from pathlib import Path


OFFICE_MEDIA_PREFIXES = {
    ".docx": "word/media/",
    ".pptx": "ppt/media/",
    ".xlsx": "xl/media/",
    ".xlsm": "xl/media/",
}

RASTER_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp"}


def script_dir() -> Path:
    return Path(__file__).resolve().parent


def has_raster_images(bundle: Path) -> bool:
    assets_dir = bundle / "raw" / "assets"
    if not assets_dir.exists():
        return False
    return any(
        path.is_file() and path.suffix.lower() in RASTER_IMAGE_SUFFIXES
        for path in assets_dir.rglob("*")
    )


def office_source_files(bundle: Path) -> list[Path]:
    roots = [bundle / "raw" / "sources", bundle / "raw" / "private"]
    files: list[Path] = []
    for root in roots:
        if root.exists():
            files.extend(
                path for path in root.rglob("*")
                if path.is_file() and path.suffix.lower() in OFFICE_MEDIA_PREFIXES
            )
    return sorted(files)


def office_media_count(source: Path) -> int:
    prefix = OFFICE_MEDIA_PREFIXES.get(source.suffix.lower())
    if not prefix:
        return 0
    try:
        with ZipFile(source) as archive:
            return len([
                name for name in archive.namelist()
                if name.startswith(prefix) and not name.endswith("/")
            ])
    except Exception:
        return 0


def preflight_office_media(bundle: Path) -> None:
    raw_assets = bundle / "raw" / "assets"
    failures: list[str] = []
    checked = 0
    with_media = 0

    for source in office_source_files(bundle):
        checked += 1
        media_count = office_media_count(source)
        if media_count == 0:
            continue
        with_media += 1
        copied_assets = sorted(raw_assets.glob(f"{source.stem}-embedded-*")) if raw_assets.exists() else []
        if len(copied_assets) < media_count:
            failures.append(
                f"- {source.relative_to(bundle)} contains {media_count} embedded media file(s), "
                f"but only {len(copied_assets)} extracted asset file(s) were found under raw/assets/."
            )

    if checked:
        print(f"Office media preflight checked {checked} Office source file(s); {with_media} contain embedded media.", flush=True)
    if failures:
        details = "\n".join(failures)
        raise SystemExit(
            "Finalization failed before export: Office source files still have embedded media "
            "that was not extracted. Run extract_source_text.py with --asset-dir raw/assets, "
            "then run create_asset_pages.py and refine the asset pages.\n"
            f"{details}"
        )


def run_step(label: str, command: list[str]) -> None:
    print(f"\n== {label} ==", flush=True)
    env = {**os.environ, "OKF_FINALIZE_RUNNING": "1"}
    result = subprocess.run(command, text=True, env=env)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def ensure_upload_not_empty(bundle: Path) -> None:
    upload_dir = bundle / "exports" / "upload"
    markdown_files = sorted(upload_dir.glob("*.md")) if upload_dir.exists() else []
    if not markdown_files:
        raise SystemExit(
            "Finalization failed: exports/upload/ contains no Markdown files. "
            "Create the OKF pages first, then rerun finalize_bundle.py."
        )


def main() -> None:
    bundle = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(".").resolve()
    scripts = script_dir()

    if not bundle.exists():
        raise SystemExit(f"Bundle path does not exist: {bundle}")

    preflight_office_media(bundle)

    if has_raster_images(bundle):
        run_step(
            "Export embedded image catalog",
            [sys.executable, str(scripts / "export_image_catalog_docx.py"), str(bundle)],
        )
    else:
        print("No raster image assets found; skipping image-catalog.docx.", flush=True)

    run_step(
        "Export upload-safe package",
        [sys.executable, str(scripts / "export_upload_package.py"), str(bundle)],
    )
    ensure_upload_not_empty(bundle)

    run_step(
        "Validate finalized bundle",
        [sys.executable, str(scripts / "validate_bundle.py"), str(bundle)],
    )

    print("\nOKF bundle finalization passed.")
    print(f"Upload package: {bundle / 'exports' / 'upload'}")
    if has_raster_images(bundle):
        print(f"Image catalog: {bundle / 'exports' / 'image-catalog.docx'}")


if __name__ == "__main__":
    main()
