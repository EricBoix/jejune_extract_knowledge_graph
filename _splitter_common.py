"""Shared utilities for the split_by_*.py splitter scripts."""
import argparse
import json
import sys
from pathlib import Path

import yaml


def source_reference(doc_dir: Path) -> str:
    return "jejune:" + doc_dir.name.removeprefix("jejune_doc_")


def load_catalog(catalog_path: str) -> tuple[dict, Path]:
    path = Path(catalog_path)
    with open(path, encoding="utf-8") as f:
        catalog = yaml.safe_load(f)
    return catalog, path.parent


def add_common_arguments(parser: argparse.ArgumentParser, modality: str) -> None:
    """Add --catalog, --output_dir, --output to an ArgumentParser."""
    parser.add_argument(
        "--catalog",
        action="append",
        metavar="CATALOG_YAML",
        required=True,
        help="Path to a jejune_doc_* catalog.yaml (repeatable).",
    )
    parser.add_argument(
        "--output_dir",
        default=None,
        metavar="DIR",
        help="Directory for the output file.",
    )
    parser.add_argument(
        "--output",
        default=None,
        metavar="OUTPUT_JSON",
        help=(
            f"Output filename relative to --output_dir; '-' writes to stdout. "
            f"Defaults to <markdown_stem>_-_{modality}_as_LangChain_document.json "
            f"placed in the markdown file's directory (single --catalog only)."
        ),
    )


def resolve_output_path(args: argparse.Namespace, modality: str) -> Path | None:
    """Return the resolved output Path, or None for stdout."""
    if args.output == "-":
        return None
    if args.output is None and len(args.catalog) > 1:
        sys.exit(
            "ERROR: --output is required when multiple --catalog arguments are provided."
        )
    if args.output is not None:
        base = Path(args.output_dir) if args.output_dir else Path(".")
        return base / args.output
    catalog, doc_dir = load_catalog(args.catalog[0])
    md_file = doc_dir / catalog["markdown_file"]
    filename = f"{md_file.stem}_-_{modality}_as_LangChain_document.json"
    out_dir = Path(args.output_dir) if args.output_dir else md_file.parent
    return out_dir / filename


def process_catalog(catalog_path: str, split_fn) -> list[dict]:
    """Load one catalog and run split_fn on its markdown file."""
    catalog, doc_dir = load_catalog(catalog_path)
    markdown_file = doc_dir / catalog["markdown_file"]
    metadata_base = {
        "source_name": str(markdown_file),
        "source_reference": source_reference(doc_dir),
    }
    return split_fn(markdown_file.read_text(encoding="utf-8"), metadata_base)


def write_output(chunks: list[dict], output_path: Path | None) -> None:
    text = json.dumps(chunks, indent=4, ensure_ascii=False)
    if output_path is None:
        print(text)
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")


def run(split_fn, modality: str, description: str) -> None:
    """Parse arguments, run split_fn over all catalogs, write output."""
    parser = argparse.ArgumentParser(description=description)
    add_common_arguments(parser, modality)
    args = parser.parse_args()
    output_path = resolve_output_path(args, modality)
    chunks = []
    for catalog_path in args.catalog:
        chunks.extend(process_catalog(catalog_path, split_fn))
    write_output(chunks, output_path)
