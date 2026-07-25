from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from eval.dataset import load_evaluation_dataset


def test_evaluation_dataset_loads(
    tmp_path: Path,
) -> None:
    dataset_path = (
        tmp_path / "ground_truth.json"
    )

    dataset_path.write_text(
        json.dumps(
            {
                "dataset_id": "sample-pair",
                "description": "Test dataset",
                "before_pid": "revision-a",
                "after_pid": "revision-b",
                "expected_changes": [
                    {
                        "change_id": "change-1",
                        "change_type": "modified",
                        "before_content": "PRESSURE 10 BARG",
                        "after_content": "PRESSURE 15 BARG",
                        "page_number": 1
                    }
                ],
                "chat_cases": [
                    {
                        "case_id": "question-1",
                        "question": "What pressure changed?",
                        "expected_grounded": True,
                        "expected_terms": [
                            "15 BARG"
                        ],
                        "expected_citation_terms": []
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = load_evaluation_dataset(
        dataset_path
    )

    assert result.dataset_id == "sample-pair"
    assert len(result.expected_changes) == 1
    assert len(result.chat_cases) == 1

    assert (
        result.expected_changes[0].after_content
        == "PRESSURE 15 BARG"
    )


def test_missing_dataset_raises_error(
    tmp_path: Path,
) -> None:
    missing_path = (
        tmp_path / "missing.json"
    )

    with pytest.raises(
        FileNotFoundError
    ):
        load_evaluation_dataset(
            missing_path
        )


def test_non_json_dataset_is_rejected(
    tmp_path: Path,
) -> None:
    dataset_path = (
        tmp_path / "dataset.txt"
    )

    dataset_path.write_text(
        "{}",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="JSON format",
    ):
        load_evaluation_dataset(
            dataset_path
        )


def test_invalid_dataset_is_rejected(
    tmp_path: Path,
) -> None:
    dataset_path = (
        tmp_path / "invalid.json"
    )

    dataset_path.write_text(
        json.dumps(
            {
                "description": "Missing required fields"
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValidationError
    ):
        load_evaluation_dataset(
            dataset_path
        )