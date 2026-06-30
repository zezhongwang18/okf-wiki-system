#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from zipfile import ZipFile
from pathlib import Path


OFFICE_MEDIA_PREFIXES = {
    ".docx": "word/media/",
    ".pptx": "ppt/media/",
    ".xlsx": "xl/media/",
    ".xlsm": "xl/media/",
}

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


def read_markdown(page: Path) -> str:
    return page.read_text(encoding="utf-8", errors="replace")


def frontmatter_value(markdown: str, key: str) -> str:
    if not markdown.startswith("---\n"):
        return ""
    end = markdown.find("\n---\n", 4)
    if end == -1:
        return ""
    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", markdown[4:end], re.MULTILINE)
    return match.group(1).strip().strip("\"'") if match else ""


def markdown_headings(markdown: str) -> set[str]:
    return {match.group(1).strip().lower() for match in re.finditer(r"^#\s+(.+)$", markdown, re.MULTILINE)}


def section_body(markdown: str, heading: str) -> str:
    pattern = re.compile(rf"^#\s+{re.escape(heading)}\s*$([\s\S]*?)(?=^#\s+|\Z)", re.MULTILINE | re.IGNORECASE)
    match = pattern.search(markdown)
    return match.group(1).strip() if match else ""


def section_has_content(markdown: str, heading: str) -> bool:
    body = section_body(markdown, heading)
    if not body:
        return False
    if re.search(r"\bTODO\b|Source Page TODO|Concept TODO|Context unavailable", body, re.I):
        return False
    return bool(re.search(r"[A-Za-z0-9\u3400-\u9fff]", body))


def is_generic_placeholder(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text).strip().lower()
    normalized = re.sub(r"^[-*]\s+", "", normalized)
    return normalized in {
        "not applicable",
        "not applicable.",
        "none",
        "none.",
        "none identified",
        "none identified.",
        "无",
        "无。",
        "不适用",
        "不适用。",
        "未提取",
        "未提取。",
    }


def has_ocr_review_marker(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text).strip().lower()
    return any(marker in normalized for marker in [
        "ocr",
        "visible text reviewed",
        "no visible text",
        "无可见文字",
        "没有可见文字",
        "公司ocr",
    ])


REQUIRED_DETAIL_SECTIONS = {
    "source": [
        "Summary",
        "Key Facts",
        "Procedures Or Workflows",
        "Rules And Exceptions",
        "Terms, Fields, Metrics, Or Parameters",
        "Evidence Snippets",
        "Questions This Source Can Answer",
        "Details Not Fully Extracted",
        "Citations",
    ],
    "concept": [
        "Overview",
        "Detailed Notes",
        "When To Use",
        "Rules And Exceptions",
        "Examples",
        "Related Sources",
        "Citations",
    ],
    "question": [
        "Answer",
        "Assets Used",
        "Evidence",
        "Caveats",
        "Related",
        "Citations",
    ],
    "asset": [
        "Description",
        "Applicable Questions",
        "Not Applicable To",
        "Source Context",
        "Visible Text",
        "Visual Notes",
        "Related",
        "Citations",
    ],
}


def page_kind(page: Path, markdown: str) -> str | None:
    rel_parts = page.parts
    doc_type = frontmatter_value(markdown, "type").lower()
    if "sources" in rel_parts or "source" in doc_type:
        return "source"
    if "concepts" in rel_parts or doc_type == "concept":
        return "concept"
    if "questions" in rel_parts or "durable" in doc_type or "question" in doc_type:
        return "question"
    if "assets" in rel_parts or "asset" in doc_type:
        return "asset"
    return None


def validate_detail_sections(bundle: Path, page: Path, errors: list[str]) -> None:
    if page.name == "index.md":
        return
    markdown = read_markdown(page)
    kind = page_kind(page.relative_to(bundle), markdown)
    if not kind:
        return
    required = REQUIRED_DETAIL_SECTIONS[kind]
    headings = markdown_headings(markdown)
    for heading in required:
        if heading.lower() not in headings:
            errors.append(f"{page.relative_to(bundle)} missing required detail section: # {heading}")
            continue
        if not section_has_content(markdown, heading):
            errors.append(f"{page.relative_to(bundle)} has empty/TODO detail section: # {heading}")
            continue
        body = section_body(markdown, heading)
        if kind in {"source", "concept", "question"} and heading not in {"Details Not Fully Extracted", "Caveats", "Assets Used"}:
            if is_generic_placeholder(body):
                errors.append(f"{page.relative_to(bundle)} has generic placeholder content in required section: # {heading}")
        if kind == "asset" and heading in {"Description", "Applicable Questions", "Source Context", "Citations"}:
            if is_generic_placeholder(body) or is_not_assigned(body):
                errors.append(f"{page.relative_to(bundle)} has non-specific asset content in required section: # {heading}")
        if kind == "asset" and heading == "Visible Text":
            if not has_ocr_review_marker(body):
                errors.append(
                    f"{page.relative_to(bundle)} # Visible Text must state OCR/visible-text review status, "
                    "or explicitly say there is no visible text."
                )


def markdown_links(markdown_block: str) -> list[str]:
    return [match.group(1).strip() for match in re.finditer(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", markdown_block)]


def normalize_reference(page: Path, reference: str) -> str:
    if re.match(r"^[a-z]+://", reference, re.I):
        return reference
    joined = (page.parent / reference).as_posix()
    parts: list[str] = []
    for part in joined.split("/"):
        if not part or part == ".":
            continue
        if part == "..":
            if parts:
                parts.pop()
        else:
            parts.append(part)
    return "/".join(parts)


def title_or_stem(page: Path, markdown: str) -> str:
    return frontmatter_value(markdown, "title") or page.stem.replace("-", " ")


def is_not_assigned(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text).strip().lower()
    return normalized in {"not assigned.", "not assigned", "none.", "none", "未分配", "未分配。"}


def validate_question_asset_links(bundle: Path, errors: list[str]) -> None:
    pages = upload_source_pages(bundle)
    asset_pages = {page.relative_to(bundle).as_posix(): page for page in pages if "assets" in page.relative_to(bundle).parts and page.name != "index.md"}
    question_pages = [page for page in pages if "questions" in page.relative_to(bundle).parts and page.name != "index.md"]

    for asset_rel, asset_page in asset_pages.items():
        markdown = read_markdown(asset_page)
        applicable = section_body(markdown, "Applicable Questions")
        if is_not_assigned(applicable):
            continue
        if not section_has_content(markdown, "Applicable Questions"):
            errors.append(f"{asset_rel} has empty/TODO detail section: # Applicable Questions")
        if not section_has_content(markdown, "Not Applicable To"):
            errors.append(f"{asset_rel} has empty/TODO detail section: # Not Applicable To")

    for question_page in question_pages:
        q_markdown = read_markdown(question_page)
        q_rel = question_page.relative_to(bundle).as_posix()
        q_title = title_or_stem(question_page, q_markdown)
        assets_used = section_body(q_markdown, "Assets Used")
        if is_not_assigned(assets_used):
            continue
        for link in markdown_links(assets_used):
            normalized = normalize_reference(Path(q_rel), link)
            if not normalized.startswith("assets/"):
                continue
            asset_page = bundle / normalized
            if not asset_page.exists():
                errors.append(f"{q_rel} references missing asset in # Assets Used: {normalized}")
                continue
            a_markdown = read_markdown(asset_page)
            applicable = section_body(a_markdown, "Applicable Questions")
            haystack = applicable.lower()
            if is_not_assigned(applicable):
                errors.append(f"{normalized} is used by {q_rel} but # Applicable Questions is Not assigned.")
                continue
            if q_rel.lower() not in haystack and q_title.lower() not in haystack:
                errors.append(
                    f"{normalized} is used by {q_rel}, but its # Applicable Questions does not mention the question title or path."
                )


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


def office_media_entries(source: Path) -> list[str]:
    prefix = OFFICE_MEDIA_PREFIXES.get(source.suffix.lower())
    if not prefix:
        return []


def load_asset_context(bundle: Path) -> list[dict]:
    context_path = bundle / "raw" / "assets" / "asset_context.json"
    if not context_path.exists():
        return []
    try:
        data = json.loads(context_path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return []
    return data if isinstance(data, list) else []
    try:
        with ZipFile(source) as archive:
            return sorted(
                name for name in archive.namelist()
                if name.startswith(prefix) and not name.endswith("/")
            )
    except Exception:
        return []


def extracted_text_candidates(source: Path) -> list[Path]:
    return [
        source.with_name(f"{source.stem}.extracted.txt"),
        source.with_suffix(".txt"),
    ]


def validate_office_media_ingest(bundle: Path, errors: list[str]) -> int:
    raw_assets = bundle / "raw" / "assets"
    context_path = raw_assets / "asset_context.json"
    context_text = context_path.read_text(encoding="utf-8", errors="replace") if context_path.exists() else ""
    contexts = load_asset_context(bundle)
    checked = 0

    for source in office_source_files(bundle):
        checked += 1
        media_entries = office_media_entries(source)
        if not media_entries:
            continue

        rel_source = source.relative_to(bundle)
        extracted_files = [path for path in extracted_text_candidates(source) if path.exists()]
        if not extracted_files:
            errors.append(
                f"{rel_source} contains {len(media_entries)} embedded media file(s), "
                "but no extracted text file was found. Run extract_source_text.py with --asset-dir raw/assets."
            )
        else:
            extracted_text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in extracted_files)
            if "Embedded Media Assets" not in extracted_text:
                errors.append(
                    f"{rel_source} contains embedded media, but extracted text does not include the Embedded Media Assets manifest."
                )

        copied_assets = sorted(raw_assets.glob(f"{source.stem}-embedded-*")) if raw_assets.exists() else []
        if len(copied_assets) < len(media_entries):
            errors.append(
                f"{rel_source} contains {len(media_entries)} embedded media file(s), "
                f"but only {len(copied_assets)} extracted asset file(s) matching raw/assets/{source.stem}-embedded-* were found."
            )

        for idx, internal_path in enumerate(media_entries, 1):
            expected_name = f"{source.stem}-embedded-{idx:02d}-{Path(internal_path).name}"
            expected_asset = raw_assets / expected_name
            if not expected_asset.exists():
                errors.append(f"{rel_source} embedded media was not extracted to expected asset: raw/assets/{expected_name}")
            manifest_line = f"`{internal_path}` ->"
            if extracted_files and manifest_line not in extracted_text:
                errors.append(f"{rel_source} extracted text manifest does not list embedded media: {internal_path}")
            matching_context = [
                item for item in contexts
                if item.get("copied_asset") == expected_name
                and item.get("source_file") == source.name
                and item.get("internal_path") == internal_path
            ]
            if context_path.exists() and not matching_context:
                errors.append(
                    f"{rel_source} asset_context.json has no exact mapping for {internal_path} -> {expected_name}."
                )

        if not context_path.exists():
            errors.append(f"{rel_source} contains embedded media, but raw/assets/asset_context.json is missing.")
        else:
            for asset in copied_assets:
                if asset.name not in context_text or source.name not in context_text:
                    errors.append(
                        f"{rel_source} embedded asset context is incomplete for raw/assets/{asset.name}."
                    )

    return checked


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


def validate_graph(bundle: Path, pages: list[Path], errors: list[str]) -> None:
    graph = bundle / "graph.yml"
    if not graph.exists():
        errors.append("Missing required path: graph.yml")
        return
    text = graph.read_text(encoding="utf-8", errors="replace")
    if "nodes:" not in text or "edges:" not in text:
        errors.append("graph.yml must contain nodes: and edges: sections.")
    for page in pages:
        rel = page.relative_to(bundle).as_posix()
        if page.name == "index.md" or rel == "log.md":
            continue
        node_id = rel.removesuffix(".md")
        if rel not in text and node_id not in text:
            errors.append(f"graph.yml missing node/reference for page: {rel}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate OKF bundle ingest completeness.")
    parser.add_argument("bundle", nargs="?", default=".", help="OKF bundle root")
    parser.add_argument("--allow-drafts", action="store_true", help="Deprecated compatibility flag; validation still fails on TODO markers")
    args = parser.parse_args()

    bundle = Path(args.bundle).resolve()
    raw_assets = bundle / "raw" / "assets"
    asset_pages = bundle / "assets"
    errors: list[str] = []
    warnings: list[str] = []

    for required in [bundle / "index.md", bundle / "log.md", bundle / "graph.yml", asset_pages, raw_assets]:
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
                errors.append(message)

    source_pages = upload_source_pages(bundle)
    for page in source_pages:
        validate_detail_sections(bundle, page, errors)
    validate_question_asset_links(bundle, errors)
    validate_graph(bundle, source_pages, errors)
    checked_office_sources = validate_office_media_ingest(bundle, errors)

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
        catalog_manifest = bundle / "exports" / "image-catalog.manifest.json"
        if not catalog.exists():
            errors.append("Image assets exist but exports/image-catalog.docx is missing.")
        else:
            embedded_count = embedded_word_media_count(catalog)
            if embedded_count < len(embeddable_images):
                errors.append(
                    "exports/image-catalog.docx does not embed all raster image bodies "
                    f"({embedded_count} embedded media file(s), {len(embeddable_images)} raster image asset(s))."
                )
        if not catalog_manifest.exists():
            errors.append("Image assets exist but exports/image-catalog.manifest.json is missing.")
        else:
            try:
                manifest = json.loads(catalog_manifest.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                manifest = []
                errors.append("exports/image-catalog.manifest.json is not valid JSON.")
            if not isinstance(manifest, list):
                errors.append("exports/image-catalog.manifest.json must be a JSON list.")
                manifest = []
            manifest_resources = {item.get("resource") for item in manifest if isinstance(item, dict)}
            for image in embeddable_images:
                resource = image.relative_to(bundle).as_posix()
                if resource not in manifest_resources:
                    errors.append(f"exports/image-catalog.manifest.json missing image resource: {resource}")

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
            allowed_files = set(expected_names)
            if embeddable_images:
                allowed_files.add("image-catalog.docx")
            exported_files = sorted(path.name for path in upload_dir.iterdir() if path.is_file())
            for name in exported_files:
                if name not in allowed_files:
                    errors.append(f"Unexpected stale or extra file in exports/upload/: {name}")
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
    if checked_office_sources:
        print(f"Checked embedded media ingest for {checked_office_sources} Office source file(s).")
    print(f"Checked {len(media_files)} raw asset(s) and {len(resources)} asset page(s).")
    if embeddable_images:
        print(f"Checked mandatory image catalog: exports/image-catalog.docx")
    if upload_sources:
        print(f"Checked mandatory upload export: exports/upload/")


if __name__ == "__main__":
    main()
