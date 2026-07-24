from __future__ import annotations

from src.canonical.model import (
    BoundingBox,
    CanonicalDocument,
    DocumentElement,
    DocumentFormat,
    ElementType,
)
from src.delta.classifier import ChangeClassificationService
from src.delta.models import (
    ChangeType,
    DocumentAlignment,
    ElementMatch,
    MatchScore,
)


def make_element(
    *,
    element_id: str,
    content: str,
    x0: float = 0.1,
    y0: float = 0.1,
    x1: float = 0.2,
    y1: float = 0.2,
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


def make_score() -> MatchScore:
    return MatchScore(
        text_similarity=1.0,
        spatial_similarity=1.0,
        type_similarity=1.0,
        total_score=1.0,
    )


def make_document(
    *,
    pid: str,
) -> CanonicalDocument:
    return CanonicalDocument(
        pid=pid,
        source_format=DocumentFormat.NATIVE_PDF,
        pages=[],
        metadata={},
    )


def classify_single_match(
    before_element: DocumentElement,
    after_element: DocumentElement,
):
    alignment = DocumentAlignment(
        matches=[
            ElementMatch(
                before=before_element,
                after=after_element,
                score=make_score(),
            )
        ],
        unmatched_before=[],
        unmatched_after=[],
    )

    return ChangeClassificationService().classify_documents(
        before=make_document(pid="revision-a"),
        after=make_document(pid="revision-b"),
        alignment=alignment,
    )


def test_identical_element_is_unchanged() -> None:
    before = make_element(
        element_id="before-1",
        content="CONTROL VALVE",
    )

    after = make_element(
        element_id="after-1",
        content="CONTROL VALVE",
    )

    delta = classify_single_match(before, after)

    assert len(delta.changes) == 1
    assert (
        delta.changes[0].change_type
        == ChangeType.UNCHANGED
    )

    assert delta.summary.unchanged == 1
    assert delta.summary.total_changes == 0


def test_changed_text_is_modified() -> None:
    before = make_element(
        element_id="before-1",
        content="DESIGN PRESSURE 286 BARG",
    )

    after = make_element(
        element_id="after-1",
        content="DESIGN PRESSURE 300 BARG",
    )

    delta = classify_single_match(before, after)

    assert (
        delta.changes[0].change_type
        == ChangeType.MODIFIED
    )

    assert delta.changes[0].text_changed is True
    assert delta.changes[0].position_changed is False
    assert delta.summary.modified == 1


def test_changed_position_is_moved() -> None:
    before = make_element(
        element_id="before-1",
        content="CONTROL VALVE",
        x0=0.1,
        y0=0.1,
        x1=0.2,
        y1=0.2,
    )

    after = make_element(
        element_id="after-1",
        content="CONTROL VALVE",
        x0=0.3,
        y0=0.3,
        x1=0.4,
        y1=0.4,
    )

    delta = classify_single_match(before, after)

    assert (
        delta.changes[0].change_type
        == ChangeType.MOVED
    )

    assert delta.changes[0].text_changed is False
    assert delta.changes[0].position_changed is True
    assert delta.summary.moved == 1


def test_changed_text_and_position_is_moved_and_modified() -> None:
    before = make_element(
        element_id="before-1",
        content="PRESSURE 286 BARG",
        x0=0.1,
        y0=0.1,
        x1=0.2,
        y1=0.2,
    )

    after = make_element(
        element_id="after-1",
        content="PRESSURE 300 BARG",
        x0=0.4,
        y0=0.4,
        x1=0.5,
        y1=0.5,
    )

    delta = classify_single_match(before, after)

    assert (
        delta.changes[0].change_type
        == ChangeType.MOVED_AND_MODIFIED
    )

    assert delta.changes[0].text_changed is True
    assert delta.changes[0].position_changed is True
    assert delta.summary.moved_and_modified == 1


def test_small_coordinate_difference_is_not_movement() -> None:
    before = make_element(
        element_id="before-1",
        content="CONTROL VALVE",
        x0=0.1,
        y0=0.1,
        x1=0.2,
        y1=0.2,
    )

    after = make_element(
        element_id="after-1",
        content="CONTROL VALVE",
        x0=0.105,
        y0=0.105,
        x1=0.205,
        y1=0.205,
    )

    delta = classify_single_match(before, after)

    assert (
        delta.changes[0].change_type
        == ChangeType.UNCHANGED
    )


def test_unmatched_before_is_removed() -> None:
    removed = make_element(
        element_id="before-1",
        content="OLD BYPASS LINE",
    )

    alignment = DocumentAlignment(
        matches=[],
        unmatched_before=[removed],
        unmatched_after=[],
    )

    delta = ChangeClassificationService().classify_documents(
        before=make_document(pid="revision-a"),
        after=make_document(pid="revision-b"),
        alignment=alignment,
    )

    assert (
        delta.changes[0].change_type
        == ChangeType.REMOVED
    )

    assert delta.changes[0].before == removed
    assert delta.changes[0].after is None
    assert delta.summary.removed == 1


def test_unmatched_after_is_added() -> None:
    added = make_element(
        element_id="after-1",
        content="NEW CONTROL VALVE",
    )

    alignment = DocumentAlignment(
        matches=[],
        unmatched_before=[],
        unmatched_after=[added],
    )

    delta = ChangeClassificationService().classify_documents(
        before=make_document(pid="revision-a"),
        after=make_document(pid="revision-b"),
        alignment=alignment,
    )

    assert (
        delta.changes[0].change_type
        == ChangeType.ADDED
    )

    assert delta.changes[0].before is None
    assert delta.changes[0].after == added
    assert delta.summary.added == 1


def test_text_comparison_ignores_case_and_spacing() -> None:
    before = make_element(
        element_id="before-1",
        content="  Control   Valve ",
    )

    after = make_element(
        element_id="after-1",
        content="CONTROL VALVE",
    )

    delta = classify_single_match(before, after)

    assert (
        delta.changes[0].change_type
        == ChangeType.UNCHANGED
    )


def test_invalid_movement_threshold_is_rejected() -> None:
    try:
        ChangeClassificationService(
            movement_threshold=1.2
        )
    except ValueError as error:
        assert "movement_threshold" in str(error)
    else:
        raise AssertionError(
            "Expected invalid threshold to raise ValueError"
        )