from __future__ import annotations

import json
from pathlib import Path

from eval.models import EvaluationDataset


def load_evaluation_dataset(
    path: str | Path,
) -> EvaluationDataset:
    """
    Load and validate an evaluation dataset from JSON.
    """

    dataset_path = Path(path)

    if not dataset_path.exists():
        raise FileNotFoundError(
            f"Evaluation dataset not found: {dataset_path}"
        )

    if dataset_path.suffix.lower() != ".json":
        raise ValueError(
            "Evaluation datasets must use JSON format."
        )

    raw_data = json.loads(
        dataset_path.read_text(
            encoding="utf-8-sig"
        )
    )

    return EvaluationDataset.model_validate(
        raw_data
    )