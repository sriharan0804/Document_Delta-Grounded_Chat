from pathlib import Path

from src.canonical.model import (
    DocumentFormat,
    ElementType,
)
from src.ingest.pdf_native import NativePDFAdapter
from src.ingest.source import DocumentSource
from src.ingest.resolver import build_local_resolver
from src.ingest.service import IngestionService


def test_native_pdf_adapter_supports_text_pdf(
    native_pdf_path: Path,
) -> None:
    adapter = NativePDFAdapter()

    source = DocumentSource(
        pid="PID-A",
        revision="A",
        file_path=native_pdf_path,
        filename=native_pdf_path.name,
    )

    assert adapter.supports(source) is True


def test_native_pdf_adapter_ingests_pdf(
    native_pdf_path: Path,
) -> None:
    adapter = NativePDFAdapter()

    source = DocumentSource(
        pid="PID-A",
        revision="A",
        file_path=native_pdf_path,
        filename=native_pdf_path.name,
    )

    document = adapter.ingest(source)

    assert document.pid == "PID-A"
    assert document.revision == "A"
    assert document.source_format == DocumentFormat.NATIVE_PDF
    assert document.page_count == 1
    assert document.element_count >= 1


def test_native_pdf_preserves_page_dimensions(
    native_pdf_path: Path,
) -> None:
    adapter = NativePDFAdapter()

    document = adapter.ingest(
        DocumentSource(
            pid="PID-A",
            file_path=native_pdf_path,
        )
    )

    page = document.pages[0]

    assert page.page_number == 1
    assert page.width == 612
    assert page.height == 792


def test_native_pdf_elements_have_bounding_boxes(
    native_pdf_path: Path,
) -> None:
    adapter = NativePDFAdapter()

    document = adapter.ingest(
        DocumentSource(
            pid="PID-A",
            file_path=native_pdf_path,
        )
    )

    assert document.pages[0].elements

    for element in document.pages[0].elements:
        assert element.bbox is not None
        assert element.bbox.width >= 0
        assert element.bbox.height >= 0


def test_native_pdf_detects_note_element(
    native_pdf_path: Path,
) -> None:
    adapter = NativePDFAdapter()

    document = adapter.ingest(
        DocumentSource(
            pid="PID-A",
            file_path=native_pdf_path,
        )
    )

    note_elements = [
        element
        for element in document.pages[0].elements
        if element.element_type == ElementType.NOTE
    ]

    assert len(note_elements) >= 1
    assert "Inspect valve" in note_elements[0].content


def test_element_ids_are_deterministic(
    native_pdf_path: Path,
) -> None:
    adapter = NativePDFAdapter()

    source = DocumentSource(
        pid="PID-A",
        file_path=native_pdf_path,
    )

    first_document = adapter.ingest(source)
    second_document = adapter.ingest(source)

    first_ids = [
        element.element_id
        for element in first_document.pages[0].elements
    ]

    second_ids = [
        element.element_id
        for element in second_document.pages[0].elements
    ]

    assert first_ids == second_ids


    def test_native_pdf_runs_through_ingestion_service(
        native_pdf_path: Path,
    ) -> None:
        resolver = build_local_resolver(
            {
                "PID-A": native_pdf_path,
            }
        )

        service = IngestionService(
            resolver=resolver,
            adapters=[
                NativePDFAdapter(),
            ],
        )

        document = service.ingest("PID-A")

        assert document.pid == "PID-A"
        assert document.source_format == DocumentFormat.NATIVE_PDF
        assert document.element_count >= 1