from __future__ import annotations

import pytest

from eval.metrics import (
    calculate_chat_metrics,
    calculate_classification_metrics,
)


def test_classification_metrics_are_calculated() -> None:
    expected = {
        "change-1",
        "change-2",
        "change-3",
        "change-4",
    }

    predicted = {
        "change-1",
        "change-2",
        "change-5",
    }

    result = calculate_classification_metrics(
        predicted=predicted,
        expected=expected,
    )

    assert result.true_positives == 2
    assert result.false_positives == 1
    assert result.false_negatives == 2

    assert result.precision == pytest.approx(
        2 / 3
    )

    assert result.recall == pytest.approx(
        2 / 4
    )

    assert result.f1 == pytest.approx(
        4 / 7
    )


def test_classification_metrics_handle_empty_inputs() -> None:
    result = calculate_classification_metrics(
        predicted=[],
        expected=[],
    )

    assert result.true_positives == 0
    assert result.false_positives == 0
    assert result.false_negatives == 0
    assert result.precision == 0.0
    assert result.recall == 0.0
    assert result.f1 == 0.0


def test_chat_metrics_are_calculated() -> None:
    result = calculate_chat_metrics(
        correctness_results=[
            True,
            True,
            False,
            True,
        ],
        groundedness_results=[
            True,
            True,
            True,
            True,
        ],
        citation_results=[
            True,
            False,
            True,
            True,
        ],
    )

    assert result.total_questions == 4
    assert result.correctness == 0.75
    assert result.groundedness == 1.0
    assert result.citation_accuracy == 0.75


def test_chat_metrics_reject_different_result_lengths() -> None:
    with pytest.raises(
        ValueError,
        match="must contain the same number",
    ):
        calculate_chat_metrics(
            correctness_results=[
                True,
                False,
            ],
            groundedness_results=[
                True,
            ],
            citation_results=[
                True,
                False,
            ],
        )


def test_chat_metrics_handle_empty_inputs() -> None:
    result = calculate_chat_metrics(
        correctness_results=[],
        groundedness_results=[],
        citation_results=[],
    )

    assert result.total_questions == 0
    assert result.correctness == 0.0
    assert result.groundedness == 0.0
    assert result.citation_accuracy == 0.0