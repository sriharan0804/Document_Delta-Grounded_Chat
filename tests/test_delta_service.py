from __future__ import annotations

from src.canonical.model import (
    BoundingBox,
    CanonicalDocument,
    CanonicalPage,
    DocumentElement,
    DocumentFormat,
    ElementType,
)
from src.delta.models import ChangeType
from src.delta.service import DocumentDeltaService


def make_element(
    *,
    element_id: str,
    content: str,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
) -> DocumentElement:
    return DocumentElement(
        element_id=element_id,
        element_type=ElementType.TEXT,
        content=content,
        bbox=BoundingBox(
            x0=x0,
            y0=y0,
            x1=x1,
            y1=y1,
        ),
        metadata={},
    )


def make_document(
    *,
    pid: str,
    elements: list[DocumentElement],
) -> CanonicalDocument:
    return CanonicalDocument(
        pid=pid,
        source_format=DocumentFormat.NATIVE_PDF,
        pages=[
            CanonicalPage(
                page_number=1,
                width=1.0,
                height=1.0,
                elements=elements,
                metadata={},
            )
        ],
        metadata={},
    )


def test_service_detects_all_change_types() -> None:
    before = make_document(
        pid="revision-a",
        elements=[
            make_element(
                element_id="a-unchanged",
                content="CONTROL VALVE",
                x0=0.1,
                y0=0.1,
                x1=0.2,
                y1=0.2,
            ),
            make_element(
                element_id="a-modified",
                content="PRESSURE 286 BARG",
                x0=0.3,
                y0=0.3,
                x1=0.4,
                y1=0.4,
            ),
            make_element(
                element_id="a-moved",
                content="FLOW TRANSMITTER",
                x0=0.5,
                y0=0.5,
                x1=0.6,
                y1=0.6,
            ),
            make_element(
                element_id="a-removed",
                content="OLD BYPASS LINE",
                x0=0.7,
                y0=0.7,
                x1=0.8,
                y1=0.8,
            ),
        ],
    )

    after = make_document(
        pid="revision-b",
        elements=[
            make_element(
                element_id="b-unchanged",
                content="CONTROL VALVE",
                x0=0.1,
                y0=0.1,
                x1=0.2,
                y1=0.2,
            ),
            make_element(
                element_id="b-modified",
                content="PRESSURE 300 BARG",
                x0=0.3,
                y0=0.3,
                x1=0.4,
                y1=0.4,
            ),
            make_element(
                element_id="b-moved",
                content="FLOW TRANSMITTER",
                x0=0.7,
                y0=0.2,
                x1=0.8,
                y1=0.3,
            ),
            make_element(
                element_id="b-added",
                content="NEW CONTROL LOOP",
                x0=0.85,
                y0=0.1,
                x1=0.95,
                y1=0.2,
            ),
        ],
    )

    result = DocumentDeltaService().compare(
        before=before,
        after=after,
    )

    change_types = {
        change.change_type
        for change in result.changes
    }

    assert ChangeType.UNCHANGED in change_types
    assert ChangeType.MODIFIED in change_types
    assert ChangeType.MOVED in change_types
    assert ChangeType.REMOVED in change_types
    assert ChangeType.ADDED in change_types

    assert result.summary.unchanged == 1
    assert result.summary.modified == 1
    assert result.summary.moved == 1
    assert result.summary.removed == 1
    assert result.summary.added == 1
    assert result.summary.total_changes == 4


def test_service_preserves_revision_ids() -> None:
    before = make_document(
        pid="revision-a",
        elements=[],
    )

    after = make_document(
        pid="revision-b",
        elements=[],
    )

    result = DocumentDeltaService().compare(
        before=before,
        after=after,
    )

    assert result.before_pid == "revision-a"
    assert result.after_pid == "revision-b"


def test_empty_documents_produce_empty_delta() -> None:
    before = make_document(
        pid="revision-a",
        elements=[],
    )

    after = make_document(
        pid="revision-b",
        elements=[],
    )

    result = DocumentDeltaService().compare(
        before=before,
        after=after,
    )

    assert result.changes == []
    assert result.summary.total_changes == 0