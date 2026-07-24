from __future__ import annotations

from collections.abc import Iterable

from src.canonical.model import (
    CanonicalDocument,
    DocumentElement,
)
from src.delta.models import (
    DocumentAlignment,
    ElementMatch,
)
from src.delta.scoring import ElementSimilarityScorer


class ElementAlignmentService:
    
    def __init__(
        self,
        *,
        scorer: ElementSimilarityScorer | None = None,
        minimum_match_score: float = 0.65,
        minimum_text_similarity: float = 0.30,
    ) -> None:
        if not 0.0 <= minimum_match_score <= 1.0:
            raise ValueError(
                "minimum_match_score must be between 0 and 1"
            )

        if not 0.0 <= minimum_text_similarity <= 1.0:
            raise ValueError(
                "minimum_text_similarity must be between 0 and 1"
            )

        self._scorer = scorer or ElementSimilarityScorer()
        self._minimum_match_score = minimum_match_score
        self._minimum_text_similarity = minimum_text_similarity

    def align(
        self,
        before_elements: Iterable[DocumentElement],
        after_elements: Iterable[DocumentElement],
    ) -> DocumentAlignment:
        before_list = list(before_elements)
        after_list = list(after_elements)

        candidate_matches = self._build_candidates(
            before_elements=before_list,
            after_elements=after_list,
        )

        # Select highest-quality pairs first.
        candidate_matches.sort(
            key=lambda match: (
                match.score.total_score,
                match.score.text_similarity,
                match.score.spatial_similarity,
            ),
            reverse=True,
        )

        matched_before_ids: set[str] = set()
        matched_after_ids: set[str] = set()
        accepted_matches: list[ElementMatch] = []

        for candidate in candidate_matches:
            before_id = candidate.before.element_id
            after_id = candidate.after.element_id

            if before_id in matched_before_ids:
                continue

            if after_id in matched_after_ids:
                continue

            accepted_matches.append(candidate)
            matched_before_ids.add(before_id)
            matched_after_ids.add(after_id)

        unmatched_before = [
            element
            for element in before_list
            if element.element_id not in matched_before_ids
        ]

        unmatched_after = [
            element
            for element in after_list
            if element.element_id not in matched_after_ids
        ]

        accepted_matches.sort(
            key=lambda match: (
                match.before.element_id,
                match.after.element_id,
            )
        )

        return DocumentAlignment(
            matches=accepted_matches,
            unmatched_before=unmatched_before,
            unmatched_after=unmatched_after,
        )

    def align_documents(
            self,
            before: CanonicalDocument,
            after: CanonicalDocument,
        ) -> DocumentAlignment:
            
            before_elements = [
                element
                for page in before.pages
                for element in page.elements
            ]
    
            after_elements = [
                element
                for page in after.pages
                for element in page.elements
            ]
    
            return self.align(
                before_elements=before_elements,
                after_elements=after_elements,
            )

    def _build_candidates(
        self,
        *,
        before_elements: list[DocumentElement],
        after_elements: list[DocumentElement],
    ) -> list[ElementMatch]:
        candidates: list[ElementMatch] = []

        for before in before_elements:
            for after in after_elements:
                if not self._is_candidate(
                    before=before,
                    after=after,
                ):
                    continue

                score = self._scorer.score(
                    before,
                    after,
                )

                if (
                    score.text_similarity
                    < self._minimum_text_similarity
                ):
                    continue

                if score.total_score < self._minimum_match_score:
                    continue

                candidates.append(
                    ElementMatch(
                        before=before,
                        after=after,
                        score=score,
                    )
                )

        return candidates

    @staticmethod
    def _is_candidate(
        *,
        before: DocumentElement,
        after: DocumentElement,
    ) -> bool:
        
        before_content = before.content.strip()
        after_content = after.content.strip()

        if not before_content:
            return False

        if not after_content:
            return False

        return True

    