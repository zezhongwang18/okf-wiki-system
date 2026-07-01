#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def read_markdown(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "page"


def frontmatter_value(markdown: str, key: str) -> str:
    if not markdown.startswith("---\n"):
        return ""
    end = markdown.find("\n---\n", 4)
    if end == -1:
        return ""
    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", markdown[4:end], re.MULTILINE)
    return match.group(1).strip().strip("\"'") if match else ""


def title_or_stem(page: Path, markdown: str) -> str:
    return frontmatter_value(markdown, "title") or page.stem.replace("-", " ")


def section_body(markdown: str, heading: str) -> str:
    pattern = re.compile(rf"^#\s+{re.escape(heading)}\s*$([\s\S]*?)(?=^#\s+|\Z)", re.MULTILINE | re.IGNORECASE)
    match = pattern.search(markdown)
    return match.group(1).strip() if match else ""


def markdown_links(markdown_block: str) -> list[tuple[str, str]]:
    return [
        (match.group(1).strip(), match.group(2).strip())
        for match in re.finditer(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)", markdown_block)
    ]


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


def resource_for_asset(bundle: Path, asset_rel: str) -> str:
    page = bundle / asset_rel
    if not page.exists():
        return ""
    return frontmatter_value(read_markdown(page), "resource")


def page_kind(page: Path, markdown: str) -> str:
    rel_parts = page.parts
    doc_type = frontmatter_value(markdown, "type").lower()
    if "questions" in rel_parts or "question" in doc_type or "durable" in doc_type:
        return "question"
    if "assets" in rel_parts or "asset" in doc_type:
        return "asset"
    if "sources" in rel_parts or "source" in doc_type:
        return "source"
    if "concepts" in rel_parts or "concept" in doc_type:
        return "concept"
    return "other"


def upload_name(page: Path) -> str:
    stem = slugify(page.stem)
    if page.name == "index.md":
        stem = f"{slugify(page.parent.name)}-index"
    return f"{stem}.md"


def iter_pages(bundle: Path) -> list[Path]:
    pages: list[Path] = []
    for path in sorted(bundle.rglob("*.md")):
        rel_parts = path.relative_to(bundle).parts
        if not rel_parts or rel_parts[0] in {"raw", "exports"}:
            continue
        if any(part.startswith(".") for part in rel_parts):
            continue
        if path.name == "index.md" or path.name == "log.md":
            continue
        pages.append(path)
    return pages


def question_export(bundle: Path, page: Path, markdown: str) -> str:
    rel = page.relative_to(bundle).as_posix()
    title = title_or_stem(page, markdown)
    assets_used = section_body(markdown, "Assets Used")
    asset_refs: list[tuple[str, str, str]] = []
    for label, target in markdown_links(assets_used):
        normalized = normalize_reference(Path(rel), target)
        if normalized.startswith("assets/"):
            asset_refs.append((label, normalized, resource_for_asset(bundle, normalized)))

    has_image = bool(asset_refs)
    allowed_lines: list[str]
    if has_image:
        allowed_lines = []
        for label, asset_page, resource in asset_refs:
            allowed_lines.append(f"- {asset_page}")
            if resource:
                allowed_lines.append(f"- {resource}")
    else:
        allowed_lines = ["none"]

    image_rule = (
        "Only use the listed assets for this exact QUESTION_ID or QUESTION_TITLE. "
        "Do not reuse these images for later questions or semantically similar questions."
        if has_image else
        "Do not attach any image to this answer. If another retrieved chunk contains an image, ignore it for this question."
    )

    return f"""QUESTION_ID:
{rel}

QUESTION_TITLE:
{title}

IMAGE_POLICY:
HAS_IMAGE: {'true' if has_image else 'false'}
ALLOWED_ASSETS:
{chr(10).join(allowed_lines)}
IMAGE_USE_RULE:
{image_rule}

ANSWER:
{section_body(markdown, 'Answer') or 'Not captured.'}

EVIDENCE:
{section_body(markdown, 'Evidence') or 'Not captured.'}

CAVEATS:
{section_body(markdown, 'Caveats') or 'Not captured.'}

RELATED:
{section_body(markdown, 'Related') or 'Not captured.'}

CITATIONS:
{section_body(markdown, 'Citations') or 'Not captured.'}

END_OF_QUESTION:
No content after this marker belongs to this question. Do not carry images or evidence across this boundary.
"""


def asset_export(bundle: Path, page: Path, markdown: str) -> str:
    rel = page.relative_to(bundle).as_posix()
    title = title_or_stem(page, markdown)
    resource = frontmatter_value(markdown, "resource")
    return f"""RETRIEVAL_GUARD:
This is image/media metadata, not standalone answer content.
Do not use this image unless the matched question page explicitly lists it in ALLOWED_ASSETS.
Do not attach this image based only on semantic similarity, shared source, shared heading, or nearby chunks.

ASSET_ID:
{rel}

ASSET_TITLE:
{title}

RESOURCE:
{resource or 'Not captured.'}

APPLICABLE_QUESTIONS:
{section_body(markdown, 'Applicable Questions') or 'Not assigned.'}

NOT_APPLICABLE_TO:
{section_body(markdown, 'Not Applicable To') or 'Not assigned.'}

DESCRIPTION:
{section_body(markdown, 'Description') or 'Not captured.'}

VISIBLE_TEXT:
{section_body(markdown, 'Visible Text') or 'Not captured.'}

SOURCE_CONTEXT:
{section_body(markdown, 'Source Context') or 'Not captured.'}

CITATIONS:
{section_body(markdown, 'Citations') or 'Not captured.'}
"""


def generic_export(bundle: Path, page: Path, markdown: str, kind: str) -> str:
    rel = page.relative_to(bundle).as_posix()
    title = title_or_stem(page, markdown)
    return f"""DOCUMENT_ID:
{rel}

DOCUMENT_TYPE:
{kind}

DOCUMENT_TITLE:
{title}

IMAGE_POLICY:
This document is not allowed to attach images directly. Images may only be used through matched question files with ALLOWED_ASSETS.

CONTENT:
{markdown}
"""


def export_rag(bundle: Path, output_dir: Path, clean: bool) -> int:
    if clean and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    used: set[Path] = set()
    for page in iter_pages(bundle):
        markdown = read_markdown(page)
        kind = page_kind(page.relative_to(bundle), markdown)
        subdir = output_dir / f"{kind}s"
        subdir.mkdir(parents=True, exist_ok=True)
        target = subdir / upload_name(page)
        if target in used:
            raise SystemExit(f"RAG upload filename collision: {target.relative_to(output_dir)}")
        used.add(target)
        if kind == "question":
            text = question_export(bundle, page, markdown)
        elif kind == "asset":
            text = asset_export(bundle, page, markdown)
        else:
            text = generic_export(bundle, page, markdown, kind)
        target.write_text(text, encoding="utf-8")
        count += 1
    return count


def main() -> None:
    if os.environ.get("OKF_FINALIZE_RUNNING") != "1":
        bundle_arg = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "."
        finalizer = Path(__file__).resolve().with_name("finalize_bundle.py")
        print(
            "export_rag_upload_package.py was called directly; delegating to finalize_bundle.py "
            "so all mandatory exports and validation happen together.",
            flush=True,
        )
        raise SystemExit(subprocess.run([sys.executable, str(finalizer), bundle_arg]).returncode)

    parser = argparse.ArgumentParser(description="Export a RAG-safe OKF upload package with question-level image policies.")
    parser.add_argument("bundle", nargs="?", default=".", help="OKF bundle root")
    parser.add_argument("--output-dir", help="Output directory; defaults to bundle/exports/rag-upload")
    parser.add_argument("--no-clean", action="store_true", help="Do not clear the output directory before export")
    args = parser.parse_args()

    bundle = Path(args.bundle).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else bundle / "exports" / "rag-upload"
    count = export_rag(bundle, output_dir, clean=not args.no_clean)
    print(f"Wrote {count} RAG-safe upload file(s) to {output_dir}.")


if __name__ == "__main__":
    main()
