from __future__ import annotations

from dataclasses import dataclass
from typing import Collection, Hashable


@dataclass(frozen=True)
class ClassificationMetrics:
    

    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float


@dataclass(frozen=True)
class ChatMetrics:
    

    total_questions: int
    correctness: float
    groundedness: float
    citation_accuracy: float


def calculate_classification_metrics(
    *,
    predicted: Collection[Hashable],
    expected: Collection[Hashable],
) -> ClassificationMetrics:
    

    predicted_set = set(predicted)
    expected_set = set(expected)

    true_positives = len(
        predicted_set.intersection(expected_set)
    )

    false_positives = len(
        predicted_set.difference(expected_set)
    )

    false_negatives = len(
        expected_set.difference(predicted_set)
    )

    precision_denominator = (
        true_positives + false_positives
    )

    recall_denominator = (
        true_positives + false_negatives
    )

    precision = (
        safe_ratio(
            numerator=true_positives,
            denominator=precision_denominator,
        )
    )

    recall = safe_ratio(
        numerator=true_positives,
        denominator=recall_denominator,
    )

    f1 = harmonic_mean(
        precision,
        recall,
    )

    return ClassificationMetrics(
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        precision=precision,
        recall=recall,
        f1=f1,
    )


def calculate_chat_metrics(
    *,
    correctness_results: Collection[bool],
    groundedness_results: Collection[bool],
    citation_results: Collection[bool],
) -> ChatMetrics:
    
   

    correctness_values = list(correctness_results)
    groundedness_values = list(groundedness_results)
    citation_values = list(citation_results)

    result_counts = {
        len(correctness_values),
        len(groundedness_values),
        len(citation_values),
    }

    if len(result_counts) != 1:
        raise ValueError(
            "Correctness, groundedness, and citation results "
            "must contain the same number of entries."
        )

    total_questions = len(correctness_values)

    if total_questions == 0:
        return ChatMetrics(
            total_questions=0,
            correctness=0.0,
            groundedness=0.0,
            citation_accuracy=0.0,
        )

    return ChatMetrics(
        total_questions=total_questions,
        correctness=boolean_accuracy(
            correctness_values
        ),
        groundedness=boolean_accuracy(
            groundedness_values
        ),
        citation_accuracy=boolean_accuracy(
            citation_values
        ),
    )


def boolean_accuracy(
    values: Collection[bool],
) -> float:
    """Return the fraction of Boolean results that are true."""

    value_list = list(values)

    if not value_list:
        return 0.0

    return sum(value_list) / len(value_list)


def harmonic_mean(
    first: float,
    second: float,
) -> float:
    """Calculate the harmonic mean of two values."""

    denominator = first + second

    if denominator == 0:
        return 0.0

    return 2 * first * second / denominator


def safe_ratio(
    *,
    numerator: int,
    denominator: int,
) -> float:
    """
    Safely calculate a metric ratio.

    A zero denominator produces zero rather than raising an exception.
    """

    if denominator == 0:
        return 0.0

    return numerator / denominator