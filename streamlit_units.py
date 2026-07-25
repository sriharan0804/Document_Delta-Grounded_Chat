from __future__ import annotations

from pathlib import Path

from src.delta.models import DocumentDelta
from src.delta.service import DocumentDeltaService
from src.ingest.docling_pdf import DoclingPDFAdapter
from src.ingest.source import DocumentSource


def compare_documents(
    before_pdf: Path,
    after_pdf: Path,
) -> DocumentDelta:
    """Ingest and compare two PDF revisions."""

    if not before_pdf.is_file():
        raise FileNotFoundError(
            f"Original PDF does not exist: {before_pdf}"
        )

    if not after_pdf.is_file():
        raise FileNotFoundError(
            f"Revised PDF does not exist: {after_pdf}"
        )

    adapter = DoclingPDFAdapter(
        enable_ocr=True,
        enable_tables=False,
    )

    before_document = adapter.ingest(
        DocumentSource(
            pid="revision-a",
            file_path=before_pdf,
            metadata={
                "revision_role": "before",
                "source_filename": before_pdf.name,
            },
        )
    )

    after_document = adapter.ingest(
        DocumentSource(
            pid="revision-b",
            file_path=after_pdf,
            metadata={
                "revision_role": "after",
                "source_filename": after_pdf.name,
            },
        )
    )

    return DocumentDeltaService().compare(
        before=before_document,
        after=after_document,
    )