from __future__ import annotations

import argparse
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import (
    DocumentConverter,
    PdfFormatOption,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test Docling PDF conversion."
    )

    parser.add_argument(
        "--file",
        required=True,
        type=Path,
        help="Path to a PDF file.",
    )

    return parser.parse_args()


def build_converter() -> DocumentConverter:
    

    pipeline_options = PdfPipelineOptions()

    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = False

    return DocumentConverter(
        allowed_formats=[
            InputFormat.PDF,
        ],
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options,
            ),
        },
    )


def main() -> None:
    args = parse_arguments()

    if not args.file.exists():
        raise FileNotFoundError(
            f"PDF does not exist: {args.file}"
        )

    if args.file.suffix.lower() != ".pdf":
        raise ValueError(
            f"Expected a PDF file, received: {args.file.suffix}"
        )

    converter = build_converter()

    print(f"Converting: {args.file}")

    result = converter.convert(
        args.file,
        max_num_pages=20,
        max_file_size=20 * 1024 * 1024,
    )

    markdown = result.document.export_to_markdown()

    print("\n--- Extracted content ---\n")
    print(markdown[:3000])

    print("\n--- Conversion summary ---")
    print(f"Characters extracted: {len(markdown)}")
    print(f"Pages found: {len(result.document.pages)}")


if __name__ == "__main__":
    print("Docling test script started")
    main()