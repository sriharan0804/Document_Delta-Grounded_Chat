from __future__ import annotations

import pytest

from src.canonical.model import (
    BoundingBox,
    DocumentElement,
    ElementType,
)
from src.delta.scoring import ElementSimilarityScorer


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


def test_identical_text_has_full_similarity() -> None:
    score = ElementSimilarityScorer.text_similarity(
        "COMPRESSOR DISCHARGE",
        "COMPRESSOR DISCHARGE",
    )

    assert score == 1.0


def test_text_similarity_ignores_case_and_whitespace() -> None:
    score = ElementSimilarityScorer.text_similarity(
        "  Compressor   Discharge ",
        "COMPRESSOR DISCHARGE",
    )

    assert score == 1.0


def test_completely_different_text_has_low_similarity() -> None:
    score = ElementSimilarityScorer.text_similarity(
        "COMPRESSOR",
        "INSTRUMENT AIR",
    )

    assert score < 0.4


def test_identical_position_has_full_similarity() -> None:
    bbox = BoundingBox(
        x0=0.1,
        y0=0.2,
        x1=0.3,
        y1=0.4,
    )

    score = ElementSimilarityScorer.spatial_similarity(
        bbox,
        bbox,
    )

    assert score == 1.0


def test_spatial_similarity_decreases_with_distance() -> None:
    first = BoundingBox(
        x0=0.0,
        y0=0.0,
        x1=0.1,
        y1=0.1,
    )

    nearby = BoundingBox(
        x0=0.1,
        y0=0.1,
        x1=0.2,
        y1=0.2,
    )

    far_away = BoundingBox(
        x0=0.8,
        y0=0.8,
        x1=0.9,
        y1=0.9,
    )

    nearby_score = ElementSimilarityScorer.spatial_similarity(
        first,
        nearby,
    )

    far_score = ElementSimilarityScorer.spatial_similarity(
        first,
        far_away,
    )

    assert nearby_score > far_score


def test_identical_elements_receive_full_total_score() -> None:
    before = make_element(
        element_id="before-1",
        content="DESIGN PRESSURE 286 BARG",
    )

    after = make_element(
        element_id="after-1",
        content="DESIGN PRESSURE 286 BARG",
    )

    result = ElementSimilarityScorer().score(
        before,
        after,
    )

    assert result.text_similarity == 1.0
    assert result.spatial_similarity == 1.0
    assert result.type_similarity == 1.0
    assert result.total_score == 1.0


def test_modified_value_still_receives_high_score() -> None:
    before = make_element(
        element_id="before-1",
        content="DESIGN PRESSURE 286 BARG",
    )

    after = make_element(
        element_id="after-1",
        content="DESIGN PRESSURE 300 BARG",
    )

    result = ElementSimilarityScorer().score(
        before,
        after,
    )

    assert result.text_similarity > 0.8
    assert result.total_score > 0.8


def test_different_element_type_reduces_score() -> None:
    before = make_element(
        element_id="before-1",
        content="NOTE 19",
        element_type=ElementType.NOTE,
    )

    after = make_element(
        element_id="after-1",
        content="NOTE 19",
        element_type=ElementType.TEXT,
    )

    result = ElementSimilarityScorer().score(
        before,
        after,
    )

    assert result.type_similarity == 0.0
    assert result.total_score < 1.0


def test_weights_must_add_up_to_one() -> None:
    with pytest.raises(
        ValueError,
        match="must add up to 1.0",
    ):
        ElementSimilarityScorer(
            text_weight=0.5,
            spatial_weight=0.2,
            type_weight=0.1,
        )


def test_negative_weight_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="cannot be negative",
    ):
        ElementSimilarityScorer(
            text_weight=0.8,
            spatial_weight=0.3,
            type_weight=-0.1,
        )