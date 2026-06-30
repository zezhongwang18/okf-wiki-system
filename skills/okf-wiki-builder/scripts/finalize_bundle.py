#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


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


def run_step(label: str, command: list[str]) -> None:
    print(f"\n== {label} ==", flush=True)
    result = subprocess.run(command, text=True)
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
