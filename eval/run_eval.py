
from __future__ import annotations

import argparse
import json
from pathlib import Path

from eval.dataset import load_evaluation_dataset
from eval.metrics import (
    calculate_chat_metrics,
    calculate_classification_metrics,
)
from eval.models import (
    EvaluationScope,
    ExpectedChange,
)
from src.delta.models import DocumentDelta, ElementDelta
from src.grounded_chat.service import GroundedChatService


def normalize_text(
    value: str | None,
) -> str:
    

    if value is None:
        return ""

    return " ".join(
        value.upper().split()
    )


def expected_change_signature(
    change: ExpectedChange,
) -> tuple[str, str, str]:
    

    return (
        change.change_type.lower(),
        normalize_text(change.before_content),
        normalize_text(change.after_content),
    )


def predicted_change_signature(
    change: ElementDelta,
) -> tuple[str, str, str]:
    

    before_content = (
        change.before.content
        if change.before is not None
        else None
    )

    after_content = (
        change.after.content
        if change.after is not None
        else None
    )

    return (
        change.change_type.value.lower(),
        normalize_text(before_content),
        normalize_text(after_content),
    )


def get_change_content(
    change: ElementDelta,
) -> str:
    

    parts: list[str] = []

    if change.before is not None:
        parts.append(change.before.content)

    if change.after is not None:
        parts.append(change.after.content)

    return normalize_text(
        " ".join(parts)
    )


def get_element_page_number(
    element: object,
) -> int | None:
    
    direct_page_number = getattr(
        element,
        "page_number",
        None,
    )

    if isinstance(direct_page_number, int):
        return direct_page_number

    direct_page_index = getattr(
        element,
        "page_index",
        None,
    )

    if isinstance(direct_page_index, int):
        return direct_page_index

    location = getattr(
        element,
        "location",
        None,
    )

    if location is not None:
        location_page_number = getattr(
            location,
            "page_number",
            None,
        )

        if isinstance(location_page_number, int):
            return location_page_number

        location_page_index = getattr(
            location,
            "page_index",
            None,
        )

        if isinstance(location_page_index, int):
            return location_page_index

    return None


def get_change_page_number(
    change: ElementDelta,
) -> int | None:
    

    if change.after is not None:
        return get_element_page_number(
            change.after
        )

    if change.before is not None:
        return get_element_page_number(
            change.before
        )

    return None


def change_is_in_scope(
    *,
    change: ElementDelta,
    scope: EvaluationScope | None,
) -> bool:
    

    if scope is None:
        return True

    content_matches = True
    page_matches = True

    if scope.content_terms:
        change_content = get_change_content(
            change
        )

        content_matches = any(
            normalize_text(term) in change_content
            for term in scope.content_terms
        )

    if scope.page_numbers:
        page_number = get_change_page_number(
            change
        )

        page_matches = (
            page_number in scope.page_numbers
        )

    return content_matches and page_matches


def load_delta_report(
    path: str | Path,
) -> DocumentDelta:
    

    delta_path = Path(path)

    if not delta_path.exists():
        raise FileNotFoundError(
            f"Delta report not found: {delta_path}"
        )

    raw_data = json.loads(
        delta_path.read_text(
            encoding="utf-8-sig"
        )
    )

    return DocumentDelta.model_validate(
        raw_data
    )


def answer_contains_terms(
    *,
    answer: str,
    expected_terms: list[str],
) -> bool:
    

    normalized_answer = normalize_text(
        answer
    )

    return all(
        normalize_text(term) in normalized_answer
        for term in expected_terms
    )


def evidence_contains_terms(
    *,
    evidence: list[object],
    expected_terms: list[str],
) -> bool:
    

    if not expected_terms:
        return True

    evidence_text = normalize_text(
        " ".join(
            str(item)
            for item in evidence
        )
    )

    return all(
        normalize_text(term) in evidence_text
        for term in expected_terms
    )

def print_unmatched_predictions(
    *,
    changes: list[ElementDelta],
    expected_signatures: set[
        tuple[str, str, str]
    ],
) -> None:
    

    unmatched_changes = [
        change
        for change in changes
        if predicted_change_signature(change)
        not in expected_signatures
    ]

    print()
    print("UNMATCHED SCOPED PREDICTIONS")
    print("-" * 60)

    if not unmatched_changes:
        print("None")
        return

    for index, change in enumerate(
        unmatched_changes,
        start=1,
    ):
        before_content = (
            change.before.content
            if change.before is not None
            else None
        )

        after_content = (
            change.after.content
            if change.after is not None
            else None
        )

        print(f"[{index}]")
        print(
            f"Type       : {change.change_type.value}"
        )
        print(
            f"Significant: {change.significant}"
        )
        print(
            f"Page       : {get_change_page_number(change)}"
        )
        print(
            f"Before     : {before_content!r}"
        )
        print(
            f"After      : {after_content!r}"
        )
        print()
def run_delta_evaluation(
    *,
    dataset_path: str | Path,
    delta_path: str | Path,
) -> None:
    """
    Run delta and Grounded Chat evaluation and print a scorecard.
    """

    dataset = load_evaluation_dataset(
        dataset_path
    )

    delta = load_delta_report(
        delta_path
    )

    expected_signatures = {
        expected_change_signature(change)
        for change in dataset.expected_changes
    }

    scoped_predicted_changes = [
    change
    for change in delta.changes
    if (
        change.significant
        and change.change_type.value.lower()
        != "unchanged"
        and change_is_in_scope(
            change=change,
            scope=dataset.evaluation_scope,
        )
    )
]

    predicted_signatures = {
        predicted_change_signature(change)
        for change in scoped_predicted_changes
    }
    print_unmatched_predictions(
            changes=scoped_predicted_changes,
            expected_signatures=expected_signatures,
        )

    delta_metrics = calculate_classification_metrics(
        predicted=predicted_signatures,
        expected=expected_signatures,
    )

    chat_service = GroundedChatService()

    correctness_results: list[bool] = []
    groundedness_results: list[bool] = []
    citation_results: list[bool] = []

    chat_case_results: list[
        tuple[str, bool, bool, bool]
    ] = []

    for chat_case in dataset.chat_cases:
        response = chat_service.answer(
            question=chat_case.question,
            delta=delta,
        )

        groundedness_correct = (
            response.grounded
            == chat_case.expected_grounded
        )

        if chat_case.expected_grounded:
            correctness = (
                response.grounded
                and answer_contains_terms(
                    answer=response.answer,
                    expected_terms=(
                        chat_case.expected_terms
                    ),
                )
            )

            citation_correct = (
                response.grounded
                and bool(response.evidence)
                and evidence_contains_terms(
                    evidence=response.evidence,
                    expected_terms=(
                        chat_case.expected_citation_terms
                    ),
                )
            )
        else:
            correctness = (
                not response.grounded
            )

            citation_correct = (
                not response.evidence
            )

        correctness_results.append(
            correctness
        )

        groundedness_results.append(
            groundedness_correct
        )

        citation_results.append(
            citation_correct
        )

        chat_case_results.append(
            (
                chat_case.case_id,
                correctness,
                groundedness_correct,
                citation_correct,
            )
        )

    chat_metrics = calculate_chat_metrics(
        correctness_results=correctness_results,
        groundedness_results=groundedness_results,
        citation_results=citation_results,
    )

    print()
    print("=" * 60)
    print("DOCUMENT DELTA & GROUNDED CHAT EVALUATION")
    print("=" * 60)

    print()
    print(f"Dataset: {dataset.dataset_id}")
    print(f"Description: {dataset.description}")

    print()
    print("DELTA EVALUATION")
    print("-" * 60)

    if dataset.evaluation_scope is None:
        print("Evaluation scope : Entire document")
    else:
        print("Evaluation scope : Labeled subset")

        if dataset.evaluation_scope.content_terms:
            print(
                "Content terms    : "
                + ", ".join(
                    dataset.evaluation_scope.content_terms
                )
            )

        if dataset.evaluation_scope.page_numbers:
            print(
                "Page numbers     : "
                + ", ".join(
                    str(page_number)
                    for page_number in (
                        dataset.evaluation_scope.page_numbers
                    )
                )
            )

    print(
        f"Expected changes : "
        f"{len(expected_signatures)}"
    )
    print(
        f"Predicted changes: "
        f"{len(predicted_signatures)}"
    )
    print(
        f"True positives   : "
        f"{delta_metrics.true_positives}"
    )
    print(
        f"False positives  : "
        f"{delta_metrics.false_positives}"
    )
    print(
        f"False negatives  : "
        f"{delta_metrics.false_negatives}"
    )
    print(
        f"Precision        : "
        f"{delta_metrics.precision:.3f}"
    )
    print(
        f"Recall           : "
        f"{delta_metrics.recall:.3f}"
    )
    print(
        f"F1               : "
        f"{delta_metrics.f1:.3f}"
    )

    print()
    print("CHAT EVALUATION")
    print("-" * 60)
    print(
        f"Questions        : "
        f"{chat_metrics.total_questions}"
    )
    print(
        f"Correctness      : "
        f"{chat_metrics.correctness:.3f}"
    )
    print(
        f"Groundedness     : "
        f"{chat_metrics.groundedness:.3f}"
    )
    print(
        f"Citation accuracy: "
        f"{chat_metrics.citation_accuracy:.3f}"
    )

    print()
    print("CHAT CASE RESULTS")
    print("-" * 60)

    for (
        case_id,
        correctness,
        groundedness,
        citation_accuracy,
    ) in chat_case_results:
        print(
            f"{case_id}: "
            f"correct={correctness}, "
            f"grounded={groundedness}, "
            f"citation={citation_accuracy}"
        )

    print()
    print("KNOWN LIMITATION")
    print("-" * 60)
    print(
        "The current delta metric uses exact normalized "
        "before/after text matching. Semantically correct changes "
        "with OCR or extraction differences may be counted as "
        "false positives or false negatives."
    )

    if dataset.evaluation_scope is not None:
        print(
            "This score covers only the explicitly labeled "
            "evaluation subset, not the entire document."
        )

    print()
    print("=" * 60)

    


def parse_arguments() -> argparse.Namespace:
    """
    Parse evaluation command-line arguments.
    """

    parser = argparse.ArgumentParser(
        description=(
            "Evaluate Document Delta and Grounded Chat."
        )
    )

    parser.add_argument(
        "--dataset",
        default=(
            "eval/datasets/"
            "sample_ground_truth.json"
        ),
        help=(
            "Path to the labeled evaluation dataset."
        ),
    )

    parser.add_argument(
        "--delta",
        default="outputs/delta_report.json",
        help=(
            "Path to the generated delta JSON report."
        ),
    )

    return parser.parse_args()


def main() -> None:
    """
    Run the evaluation command.
    """

    args = parse_arguments()

    run_delta_evaluation(
        dataset_path=args.dataset,
        delta_path=args.delta,
    )


if __name__ == "__main__":
    main()

