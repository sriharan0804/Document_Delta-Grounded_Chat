from __future__ import annotations

import pytest

from src.canonical.model import (
    BoundingBox,
    DocumentElement,
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


def make_alignment(
    *,
    before: DocumentElement,
    after: DocumentElement,
) -> DocumentAlignment:
    return DocumentAlignment(
        matches=[
            ElementMatch(
                before=before,
                after=after,
                score=make_score(),
            )
        ],
        unmatched_before=[],
        unmatched_after=[],
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

    delta = ChangeClassificationService().classify(
        before_pid="revision-a",
        after_pid="revision-b",
        alignment=make_alignment(
            before=before,
            after=after,
        ),
    )

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

    delta = ChangeClassificationService().classify(
        before_pid="revision-a",
        after_pid="revision-b",
        alignment=make_alignment(
            before=before,
            after=after,
        ),
    )

    change = delta.changes[0]

    assert change.change_type == ChangeType.MODIFIED
    assert change.text_changed is True
    assert change.position_changed is False
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

    delta = ChangeClassificationService().classify(
        before_pid="revision-a",
        after_pid="revision-b",
        alignment=make_alignment(
            before=before,
            after=after,
        ),
    )

    change = delta.changes[0]

    assert change.change_type == ChangeType.MOVED
    assert change.text_changed is False
    assert change.position_changed is True
    assert delta.summary.moved == 1


def test_changed_text_and_position() -> None:
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

    delta = ChangeClassificationService().classify(
        before_pid="revision-a",
        after_pid="revision-b",
        alignment=make_alignment(
            before=before,
            after=after,
        ),
    )

    change = delta.changes[0]

    assert (
        change.change_type
        == ChangeType.MOVED_AND_MODIFIED
    )
    assert change.text_changed is True
    assert change.position_changed is True
    assert delta.summary.moved_and_modified == 1


def test_small_position_difference_is_unchanged() -> None:
    before = make_element(
        element_id="before-1",
        content="CONTROL VALVE",
    )

    after = make_element(
        element_id="after-1",
        content="CONTROL VALVE",
        x0=0.105,
        y0=0.105,
        x1=0.205,
        y1=0.205,
    )

    delta = ChangeClassificationService().classify(
        before_pid="revision-a",
        after_pid="revision-b",
        alignment=make_alignment(
            before=before,
            after=after,
        ),
    )

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

    delta = ChangeClassificationService().classify(
        before_pid="revision-a",
        after_pid="revision-b",
        alignment=alignment,
    )

    assert (
        delta.changes[0].change_type
        == ChangeType.REMOVED
    )
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

    delta = ChangeClassificationService().classify(
        before_pid="revision-a",
        after_pid="revision-b",
        alignment=alignment,
    )

    assert (
        delta.changes[0].change_type
        == ChangeType.ADDED
    )
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

    delta = ChangeClassificationService().classify(
        before_pid="revision-a",
        after_pid="revision-b",
        alignment=make_alignment(
            before=before,
            after=after,
        ),
    )

    assert (
        delta.changes[0].change_type
        == ChangeType.UNCHANGED
    )


def test_invalid_movement_threshold_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="movement_threshold",
    ):
        ChangeClassificationService(
            movement_threshold=1.2
        )