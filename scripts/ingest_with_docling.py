from __future__ import annotations

import argparse
from pathlib import Path

from src.ingest.docling_pdf import DoclingPDFAdapter
from src.ingest.source import DocumentSource


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest a PDF using the Docling adapter."
    )

    parser.add_argument(
        "--pdf",
        type=Path,
        default=Path("data/samples/revision_a.pdf"),
        help="Path to the PDF file.",
    )

    parser.add_argument(
        "--pid",
        default="revision-a",
        help="Document identifier.",
    )

    parser.add_argument(
        "--ocr",
        action="store_true",
        help="Allow OCR fallback when native extraction is insufficient.",
    )

    parser.add_argument(
        "--show-elements",
        type=int,
        default=20,
        help="Number of extracted elements to display.",
    )

    return parser


def resolve_pdf_path(
    project_root: Path,
    provided_path: Path,
) -> Path:
    if provided_path.is_absolute():
        return provided_path.resolve()

    return (project_root / provided_path).resolve()


def main() -> None:
    args = build_parser().parse_args()

    project_root = Path(__file__).resolve().parents[1]

    pdf_path = resolve_pdf_path(
        project_root=project_root,
        provided_path=args.pdf,
    )

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"PDF does not exist: {pdf_path}"
        )

    if not pdf_path.is_file():
        raise ValueError(
            f"PDF path is not a file: {pdf_path}"
        )

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(
            f"Expected a PDF file: {pdf_path}"
        )

    print(f"PDF: {pdf_path}")
    print(f"OCR fallback enabled: {args.ocr}")
    print("Starting ingestion...\n")

    source = DocumentSource(
        pid=args.pid,
        file_path=pdf_path,
        metadata={
            "source_filename": pdf_path.name,
            "source_path": str(pdf_path),
        },
    )

    adapter = DoclingPDFAdapter(
        enable_ocr=args.ocr,
        enable_tables=False,
    )

    document = adapter.ingest(source)

    element_count = sum(
        len(page.elements)
        for page in document.pages
    )

    print("\n--- Ingestion result ---")
    print(f"Document ID: {document.pid}")
    print(f"Pages: {len(document.pages)}")
    print(f"Elements: {element_count}")
    print(f"Metadata: {document.metadata}")

    remaining_elements = args.show_elements

    if remaining_elements <= 0:
        return

    print("\n--- Extracted elements ---")

    for page in document.pages:
        if remaining_elements <= 0:
            break

        print(f"\nPage {page.page_number}")

        page_elements = page.elements[
            :remaining_elements
        ]

        for element in page_elements:
            content = element.content.strip()

            if not content:
                continue

            print(
                f"- [{element.element_type}] "
                f"{content!r}"
            )

            remaining_elements -= 1

            if remaining_elements <= 0:
                break


if __name__ == "__main__":
    main()