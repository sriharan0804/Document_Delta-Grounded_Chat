from __future__ import annotations

from pathlib import Path

from src.ingest.docling_pdf import DoclingPDFAdapter
from src.ingest.source import DocumentSource


def main() -> None:
    source = DocumentSource(
        pid="revision-a",
        file_path=Path("scripts/revision_a.pdf"),
        metadata={
            "revision": "A",
        },
    )

    adapter = DoclingPDFAdapter(
        enable_ocr=True,
        enable_tables=False,
    )

    document = adapter.ingest(source)

    print("\n--- Canonical document ---")
    print(f"Document ID: {document.pid}")
    print(f"Pages: {document.page_count}")
    print(f"Elements: {document.element_count}")

    for page in document.pages:
        print(
            f"Page {page.page_number}: "
            f"{len(page.elements)} elements"
        )

        for element in page.elements[:10]:
            print(
                element.element_id,
                element.element_type,
                repr(element.content),
            )


if __name__ == "__main__":
    main()