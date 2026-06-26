#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
import shutil
from pathlib import Path
from typing import Optional
from zipfile import ZipFile
from xml.etree import ElementTree as ET


NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}

MEDIA_PREFIXES = {
    ".docx": "word/media/",
    ".pptx": "ppt/media/",
    ".xlsx": "xl/media/",
    ".xlsm": "xl/media/",
}


def clean(lines: list[str]) -> str:
    out: list[str] = []
    for line in lines:
        line = line.encode("utf-8", "replace").decode("utf-8")
        line = re.sub(r"[\t\r]+", " ", line)
        line = re.sub(r" {2,}", " ", line).strip()
        if line:
            out.append(line)
    return "\n".join(out) + ("\n" if out else "")


def copy_office_media(zf: ZipFile, source_path: Path, media_prefix: str, asset_dir: Optional[Path]) -> list[str]:
    media_names = sorted(name for name in zf.namelist() if name.startswith(media_prefix) and not name.endswith("/"))
    if not media_names:
        return []

    lines = ["", "## Embedded Media Assets"]
    lines.append(f"Found {len(media_names)} embedded media file(s) under `{media_prefix}`.")
    if asset_dir:
        asset_dir.mkdir(parents=True, exist_ok=True)
    else:
        lines.append("No asset directory was provided, so embedded files were not copied. Re-run with `--asset-dir raw/assets` to preserve them.")

    for idx, name in enumerate(media_names, 1):
        original_name = Path(name).name
        copied_path = None
        if asset_dir:
            target_name = f"{source_path.stem}-embedded-{idx:02d}-{original_name}"
            target = asset_dir / target_name
            with zf.open(name) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            copied_path = target

        if copied_path:
            lines.append(f"- `{name}` -> `{copied_path}`")
        else:
            lines.append(f"- `{name}`")
    return lines


def extract_docx(path: Path, asset_dir: Optional[Path] = None) -> str:
    with ZipFile(path) as zf:
        tree = ET.fromstring(zf.read("word/document.xml"))
        lines = []
        for para in tree.findall(".//w:p", NS):
            text = "".join(t.text or "" for t in para.findall(".//w:t", NS)).strip()
            if text:
                lines.append(text)
        lines.extend(copy_office_media(zf, path, MEDIA_PREFIXES[".docx"], asset_dir))
    return clean(lines)


def extract_pptx(path: Path, asset_dir: Optional[Path] = None) -> str:
    lines = []
    with ZipFile(path) as zf:
        slides = sorted(
            [name for name in zf.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", name)],
            key=lambda name: int(re.search(r"slide(\d+)\.xml", name).group(1)),
        )
        for idx, name in enumerate(slides, 1):
            tree = ET.fromstring(zf.read(name))
            slide_lines = []
            for para in tree.findall(".//a:p", NS):
                text = "".join(t.text or "" for t in para.findall(".//a:t", NS)).strip()
                if text:
                    slide_lines.append(text)
            if slide_lines:
                lines.append(f"## Slide {idx}")
                lines.extend(slide_lines)
        lines.extend(copy_office_media(zf, path, MEDIA_PREFIXES[".pptx"], asset_dir))
    return clean(lines)


def extract_pdf(path: Path) -> str:
    try:
        import fitz  # type: ignore

        doc = fitz.open(path)
        lines = []
        for idx, page in enumerate(doc, 1):
            text = page.get_text("text") or ""
            if text.strip():
                lines.append(f"## Page {idx}")
                lines.extend(text.splitlines())
        return clean(lines)
    except Exception:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(path))
        lines = []
        for idx, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""
            if text.strip():
                lines.append(f"## Page {idx}")
                lines.extend(text.splitlines())
        return clean(lines)


def extract_workbook(path: Path, asset_dir: Optional[Path] = None) -> str:
    try:
        from openpyxl import load_workbook  # type: ignore
    except Exception as exc:
        raise SystemExit("Excel extraction requires openpyxl in the active Python environment.") from exc

    lines = []
    with ZipFile(path) as zf:
        lines.extend(copy_office_media(zf, path, MEDIA_PREFIXES[path.suffix.lower()], asset_dir))

    workbook = load_workbook(path, data_only=False, read_only=True)
    lines.extend([
        f"# Workbook: {path.name}",
        f"Sheets: {', '.join(workbook.sheetnames)}",
    ])
    for sheet in workbook.worksheets:
        lines.append("")
        lines.append(f"## Sheet: {sheet.title}")
        lines.append(f"Dimensions: {sheet.max_row} rows x {sheet.max_column} columns")

        non_empty_rows = []
        formula_count = 0
        for row in sheet.iter_rows():
            values = []
            has_value = False
            for cell in row:
                value = cell.value
                if isinstance(value, str) and value.startswith("="):
                    formula_count += 1
                if value is not None:
                    has_value = True
                values.append("" if value is None else str(value))
            if has_value:
                non_empty_rows.append(values)
            if len(non_empty_rows) >= 21:
                # Keep output compact: one likely header row plus up to 20 sample rows.
                break

        lines.append(f"Formula cells sampled/full scan estimate: {formula_count}")
        if non_empty_rows:
            header = non_empty_rows[0]
            lines.append("### Header / First Non-empty Row")
            lines.append(" | ".join(header))
            if len(non_empty_rows) > 1:
                lines.append("### Sample Rows")
                for row in non_empty_rows[1:]:
                    lines.append(" | ".join(row))
        else:
            lines.append("Sheet appears empty.")

    return clean(lines)


def extract_delimited(path: Path, delimiter: str) -> str:
    lines = [f"# Table: {path.name}"]
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle, delimiter=delimiter)
        for idx, row in enumerate(reader):
            if idx == 0:
                lines.append("## Header / First Row")
            elif idx == 1:
                lines.append("## Sample Rows")
            if idx > 20:
                lines.append("... sample truncated after 20 rows")
                break
            lines.append(" | ".join(row))
    return clean(lines)


def extract_image_metadata(path: Path) -> str:
    try:
        from PIL import Image, ExifTags  # type: ignore
    except Exception as exc:
        raise SystemExit("Image metadata extraction requires Pillow in the active Python environment.") from exc

    with Image.open(path) as image:
        lines = [
            f"# Image Asset: {path.name}",
            f"Format: {image.format}",
            f"Mode: {image.mode}",
            f"Size: {image.width} x {image.height}",
        ]
        exif = image.getexif()
        if exif:
            lines.append("## EXIF")
            for key, value in list(exif.items())[:40]:
                label = ExifTags.TAGS.get(key, str(key))
                lines.append(f"- {label}: {value}")
        lines.append("")
        lines.append("## Visual Description")
        lines.append("Add an LLM-generated visual description after inspecting the image with available vision tools.")
        lines.append("")
        lines.append("## OCR")
        lines.append("Add OCR text if a reliable OCR tool is available or if the visible text can be read manually.")
        return clean(lines)


def extract(path: Path, asset_dir: Optional[Path] = None) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf(path)
    if suffix == ".docx":
        return extract_docx(path, asset_dir=asset_dir)
    if suffix == ".pptx":
        return extract_pptx(path, asset_dir=asset_dir)
    if suffix in {".xlsx", ".xlsm"}:
        return extract_workbook(path, asset_dir=asset_dir)
    if suffix == ".csv":
        return extract_delimited(path, ",")
    if suffix == ".tsv":
        return extract_delimited(path, "\t")
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}:
        return extract_image_metadata(path)
    if suffix in {".txt", ".md", ".html", ".htm", ".json", ".yaml", ".yml"}:
        return path.read_text(encoding="utf-8", errors="replace")
    raise SystemExit(f"Unsupported source type: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract searchable text from source files.")
    parser.add_argument("source", help="Source file")
    parser.add_argument("output", nargs="?", help="Output .txt file")
    parser.add_argument("--asset-dir", help="Directory for preserving embedded Office media assets")
    args = parser.parse_args()

    source = Path(args.source)
    output = Path(args.output) if args.output else source.with_suffix(".txt")
    asset_dir = Path(args.asset_dir) if args.asset_dir else None
    text = extract(source, asset_dir=asset_dir)
    output.write_text(text, encoding="utf-8", errors="replace")
    print(f"Wrote {output} ({len(text)} chars)")


if __name__ == "__main__":
    main()
