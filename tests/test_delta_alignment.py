from __future__ import annotations

import pytest

from src.canonical.model import (
    BoundingBox,
    DocumentElement,
    ElementType,
)
from src.delta.alignment import ElementAlignmentService


def make_element(
    *,
    element_id: str,
    content: str,
    x0: float = 0.1,
    y0: float = 0.1,
    x1: float = 0.2,
    y1: float = 0.2,
    element_type: ElementType = ElementType.TEXT,
) -> DocumentElement:
    return DocumentElement(
        element_id=element_id,
        element_type=element_type,
        content=content,
        bbox=BoundingBox(
            x0=x0,
            y0=y0,
            x1=x1,
            y1=y1,
        ),
        metadata={},
    )


def test_identical_elements_are_matched() -> None:
    before = make_element(
        element_id="before-1",
        content="DESIGN PRESSURE 286 BARG",
    )

    after = make_element(
        element_id="after-1",
        content="DESIGN PRESSURE 286 BARG",
    )

    alignment = ElementAlignmentService().align(
        [before],
        [after],
    )

    assert alignment.match_count == 1
    assert alignment.added_count == 0
    assert alignment.removed_count == 0

    match = alignment.matches[0]

    assert match.before.element_id == "before-1"
    assert match.after.element_id == "after-1"
    assert match.score.total_score == 1.0


def test_modified_value_is_still_matched() -> None:
    before = make_element(
        element_id="before-1",
        content="DESIGN PRESSURE 286 BARG",
    )

    after = make_element(
        element_id="after-1",
        content="DESIGN PRESSURE 300 BARG",
    )

    alignment = ElementAlignmentService().align(
        [before],
        [after],
    )

    assert alignment.match_count == 1
    assert alignment.added_count == 0
    assert alignment.removed_count == 0


def test_unrelated_elements_remain_unmatched() -> None:
    before = make_element(
        element_id="before-1",
        content="COMPRESSOR DISCHARGE",
    )

    after = make_element(
        element_id="after-1",
        content="INSTRUMENT AIR",
    )

    alignment = ElementAlignmentService().align(
        [before],
        [after],
    )

    assert alignment.match_count == 0
    assert alignment.removed_count == 1
    assert alignment.added_count == 1


def test_added_element_is_reported_as_unmatched_after() -> None:
    existing_before = make_element(
        element_id="before-1",
        content="COMPRESSOR DISCHARGE",
    )

    existing_after = make_element(
        element_id="after-1",
        content="COMPRESSOR DISCHARGE",
    )

    added_after = make_element(
        element_id="after-2",
        content="NEW CONTROL VALVE",
        x0=0.5,
        y0=0.5,
        x1=0.6,
        y1=0.6,
    )

    alignment = ElementAlignmentService().align(
        [existing_before],
        [existing_after, added_after],
    )

    assert alignment.match_count == 1
    assert alignment.removed_count == 0
    assert alignment.added_count == 1

    assert (
        alignment.unmatched_after[0].element_id
        == "after-2"
    )


def test_removed_element_is_reported_as_unmatched_before() -> None:
    existing_before = make_element(
        element_id="before-1",
        content="COMPRESSOR DISCHARGE",
    )

    removed_before = make_element(
        element_id="before-2",
        content="OLD BYPASS LINE",
        x0=0.5,
        y0=0.5,
        x1=0.6,
        y1=0.6,
    )

    existing_after = make_element(
        element_id="after-1",
        content="COMPRESSOR DISCHARGE",
    )

    alignment = ElementAlignmentService().align(
        [existing_before, removed_before],
        [existing_after],
    )

    assert alignment.match_count == 1
    assert alignment.removed_count == 1
    assert alignment.added_count == 0

    assert (
        alignment.unmatched_before[0].element_id
        == "before-2"
    )


def test_after_element_cannot_be_matched_twice() -> None:
    before_one = make_element(
        element_id="before-1",
        content="CONTROL VALVE",
    )

    before_two = make_element(
        element_id="before-2",
        content="CONTROL VALVE",
        x0=0.7,
        y0=0.7,
        x1=0.8,
        y1=0.8,
    )

    after = make_element(
        element_id="after-1",
        content="CONTROL VALVE",
    )

    alignment = ElementAlignmentService().align(
        [before_one, before_two],
        [after],
    )

    assert alignment.match_count == 1
    assert alignment.removed_count == 1
    assert alignment.added_count == 0

    assert (
        alignment.matches[0].before.element_id
        == "before-1"
    )


def test_closest_identical_element_is_selected() -> None:
    before = make_element(
        element_id="before-1",
        content="CONTROL VALVE",
        x0=0.1,
        y0=0.1,
        x1=0.2,
        y1=0.2,
    )

    nearby_after = make_element(
        element_id="after-near",
        content="CONTROL VALVE",
        x0=0.12,
        y0=0.12,
        x1=0.22,
        y1=0.22,
    )

    distant_after = make_element(
        element_id="after-far",
        content="CONTROL VALVE",
        x0=0.8,
        y0=0.8,
        x1=0.9,
        y1=0.9,
    )

    alignment = ElementAlignmentService().align(
        [before],
        [distant_after, nearby_after],
    )

    assert alignment.match_count == 1
    assert (
        alignment.matches[0].after.element_id
        == "after-near"
    )

    assert alignment.added_count == 1
    assert (
        alignment.unmatched_after[0].element_id
        == "after-far"
    )


def test_empty_inputs_return_empty_alignment() -> None:
    alignment = ElementAlignmentService().align(
        [],
        [],
    )

    assert alignment.match_count == 0
    assert alignment.removed_count == 0
    assert alignment.added_count == 0


def test_invalid_minimum_match_score_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="minimum_match_score",
    ):
        ElementAlignmentService(
            minimum_match_score=1.1
        )


def test_invalid_minimum_text_similarity_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="minimum_text_similarity",
    ):
        ElementAlignmentService(
            minimum_text_similarity=-0.1
        )