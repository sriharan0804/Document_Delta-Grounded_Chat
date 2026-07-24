from __future__ import annotations

from difflib import SequenceMatcher

from src.canonical.model import (
    BoundingBox,
    DocumentElement,
)
from src.delta.models import MatchScore


class ElementSimilarityScorer:
    

    def __init__(
        self,
        *,
        text_weight: float = 0.65,
        spatial_weight: float = 0.25,
        type_weight: float = 0.10,
    ) -> None:
        weights = (
            text_weight,
            spatial_weight,
            type_weight,
        )

        if any(weight < 0 for weight in weights):
            raise ValueError("Similarity weights cannot be negative")

        total_weight = sum(weights)

        if abs(total_weight - 1.0) > 1e-9:
            raise ValueError(
                "Similarity weights must add up to 1.0"
            )

        self._text_weight = text_weight
        self._spatial_weight = spatial_weight
        self._type_weight = type_weight

    def score(
        self,
        before: DocumentElement,
        after: DocumentElement,
    ) -> MatchScore:
        text_similarity = self.text_similarity(
            before.content,
            after.content,
        )

        spatial_similarity = self.spatial_similarity(
            before.bbox,
            after.bbox,
        )

        type_similarity = (
            1.0
            if before.element_type == after.element_type
            else 0.0
        )

        total_score = (
            text_similarity * self._text_weight
            + spatial_similarity * self._spatial_weight
            + type_similarity * self._type_weight
        )

        return MatchScore(
            text_similarity=text_similarity,
            spatial_similarity=spatial_similarity,
            type_similarity=type_similarity,
            total_score=max(0.0, min(1.0, total_score)),
        )

    @staticmethod
    def text_similarity(
        before_text: str,
        after_text: str,
    ) -> float:
        normalized_before = (
            ElementSimilarityScorer._normalize_text(before_text)
        )
        normalized_after = (
            ElementSimilarityScorer._normalize_text(after_text)
        )

        if not normalized_before and not normalized_after:
            return 1.0

        if not normalized_before or not normalized_after:
            return 0.0

        if normalized_before == normalized_after:
            return 1.0

        return SequenceMatcher(
            None,
            normalized_before,
            normalized_after,
        ).ratio()

    @staticmethod
    def spatial_similarity(
        before_bbox: BoundingBox,
        after_bbox: BoundingBox,
    ) -> float:
        

        before_center_x = (
            before_bbox.x0 + before_bbox.x1
        ) / 2

        before_center_y = (
            before_bbox.y0 + before_bbox.y1
        ) / 2

        after_center_x = (
            after_bbox.x0 + after_bbox.x1
        ) / 2

        after_center_y = (
            after_bbox.y0 + after_bbox.y1
        ) / 2

        horizontal_distance = abs(
            before_center_x - after_center_x
        )

        vertical_distance = abs(
            before_center_y - after_center_y
        )

        # Manhattan distance can range from 0 to 2 because coordinates
        # are normalized between 0 and 1.
        normalized_distance = (
            horizontal_distance + vertical_distance
        ) / 2

        return max(
            0.0,
            min(1.0, 1.0 - normalized_distance),
        )

    @staticmethod
    def _normalize_text(text: str) -> str:
        return " ".join(text.upper().split())