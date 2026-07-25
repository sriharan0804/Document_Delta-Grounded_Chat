from __future__ import annotations

import re

from src.delta.models import (
    ChangeType,
    DocumentDelta,
    ElementDelta,
)
from src.grounded_chat.models import (
    ChangeEvidence,
    GroundedChatResponse,
)


class GroundedChatService:

    _STOP_WORDS = {
        "WHAT",
        "WHICH",
        "WHERE",
        "WHEN",
        "WERE",
        "WAS",
        "ARE",
        "THE",
        "ABOUT",
        "CHANGED",
        "CHANGE",
        "CHANGES",
        "VALUE",
        "VALUES",
        "SHOW",
        "TELL",
        "FROM",
        "WITH",
        "THAT",
        "THIS",
    }

    def answer(
        self,
        *,
        question: str,
        delta: DocumentDelta,
    ) -> GroundedChatResponse:
        normalized_question = question.strip().upper()

        ranked_changes = []

        for change in delta.changes:
            if not change.significant:
                continue

            if change.change_type == ChangeType.UNCHANGED:
                continue

            relevance_score = self._relevance_score(
                question=normalized_question,
                change=change,
            )

            if relevance_score <= 0:
                continue

            ranked_changes.append(
                (
                    relevance_score,
                    change,
                )
            )

        ranked_changes.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        relevant_changes = [
            change
            for _, change in ranked_changes[:10]
        ]

        if not relevant_changes:
            return GroundedChatResponse(
                answer=(
                    "I could not find evidence in the document "
                    "revision delta that answers this question."
                ),
                evidence=[],
                grounded=False,
            )

        evidence = [
            self._build_evidence(change)
            for change in relevant_changes
        ]

        return GroundedChatResponse(
            answer=self._build_answer(
                question=question,
                evidence=evidence,
            ),
            evidence=evidence,
            grounded=True,
        )

    def _relevance_score(
        self,
        *,
        question: str,
        change: ElementDelta,
    ) -> float:
        question_terms = self._extract_terms(question)

        if not question_terms:
            return 0.0

        before_content = (
            change.before.content
            if change.before is not None
            else ""
        )

        after_content = (
            change.after.content
            if change.after is not None
            else ""
        )

        combined_text = (
            f"{before_content} {after_content}"
        ).upper()

        matching_terms = {
            term
            for term in question_terms
            if term in combined_text
        }

        if not matching_terms:
            return 0.0

        score = float(len(matching_terms))

        if change.change_type == ChangeType.MODIFIED:
            score += 3.0
        elif change.change_type == ChangeType.MOVED_AND_MODIFIED:
            score += 2.5
        elif change.change_type in {
            ChangeType.ADDED,
            ChangeType.REMOVED,
        }:
            score += 1.0

        before_numbers = self._extract_measurement_numbers(
            before_content
        )

        after_numbers = self._extract_measurement_numbers(
            after_content
        )

        asks_about_values = bool(
            {"VALUE", "VALUES"} & self._raw_terms(question)
        )

        if asks_about_values:
            if before_numbers and after_numbers:
                if before_numbers != after_numbers:
                    score += 5.0
                else:
                    score -= 4.0
            elif before_numbers or after_numbers:
                score += 1.0
            else:
                score -= 2.0

        return score

    def _extract_terms(
        self,
        text: str,
    ) -> set[str]:
        return {
            term
            for term in self._raw_terms(text)
            if len(term) >= 3
            and term not in self._STOP_WORDS
        }

    @staticmethod
    def _raw_terms(
        text: str,
    ) -> set[str]:
        return set(
            re.findall(
                r"[A-Z0-9]+",
                text.upper(),
            )
        )

    @staticmethod
    def _extract_measurement_numbers(
        text: str,
    ) -> list[str]:
        normalized = re.sub(
            r"^\s*\d+\.\s*",
            "",
            text,
        )

        return re.findall(
            r"\d+(?:\.\d+)?",
            normalized,
        )

    @staticmethod
    def _build_evidence(
        change: ElementDelta,
    ) -> ChangeEvidence:
        return ChangeEvidence(
            change_type=change.change_type,
            before_content=(
                change.before.content
                if change.before is not None
                else None
            ),
            after_content=(
                change.after.content
                if change.after is not None
                else None
            ),
            before_element_id=(
                change.before.element_id
                if change.before is not None
                else None
            ),
            after_element_id=(
                change.after.element_id
                if change.after is not None
                else None
            ),
            significant=change.significant,
        )

    @staticmethod
    def _build_answer(
        *,
        question: str,
        evidence: list[ChangeEvidence],
    ) -> str:
        lines = [
            (
                "Based on the detected revision changes "
                f"for the question '{question}':"
            )
        ]

        for index, item in enumerate(
            evidence,
            start=1,
        ):
            before = (
                item.before_content
                or "not present"
            )

            after = (
                item.after_content
                or "not present"
            )

            lines.append(
                f"[{index}] "
                f"{item.change_type.value}: "
                f"'{before}' → '{after}'"
            )

        return "\n".join(lines)