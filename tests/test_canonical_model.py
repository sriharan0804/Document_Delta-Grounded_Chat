import pytest
from pydantic import ValidationError

from src.canonical.model import (
    BoundingBox,
    CanonicalDocument,
    CanonicalPage,
    DocumentElement,
    DocumentFormat,
    ElementType,
)


def test_bounding_box_calculates_dimensions() -> None:
    bbox = BoundingBox(
        x0=10,
        y0=20,
        x1=110,
        y1=70,
    )

    assert bbox.width == 100
    assert bbox.height == 50


def test_bounding_box_rejects_invalid_coordinates() -> None:
    with pytest.raises(ValidationError):
        BoundingBox(
            x0=100,
            y0=20,
            x1=50,
            y1=70,
        )


def test_canonical_document_counts_pages_and_elements() -> None:
    document = CanonicalDocument(
        pid="PID-REV-A",
        revision="A",
        source_format=DocumentFormat.NATIVE_PDF,
        filename="revision-a.pdf",
        pages=[
            CanonicalPage(
                page_number=1,
                width=612,
                height=792,
                elements=[
                    DocumentElement(
                        element_id="page-1-element-1",
                        element_type=ElementType.NOTE,
                        content="Maximum operating pressure is 10 bar.",
                        bbox=BoundingBox(
                            x0=20,
                            y0=30,
                            x1=250,
                            y1=60,
                        ),
                    )
                ],
            )
        ],
    )

    assert document.page_count == 1
    assert document.element_count == 1
    assert document.get_element("page-1-element-1") is not None
    assert document.get_element("missing-element") is None


def test_document_can_be_serialized_to_json() -> None:
    document = CanonicalDocument(
        pid="PID-REV-B",
        revision="B",
        source_format=DocumentFormat.SCANNED_PDF,
        pages=[],
    )

    json_output = document.model_dump_json()

    assert "PID-REV-B" in json_output
    assert "scanned_pdf" in json_output