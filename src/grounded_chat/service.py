from __future__ import annotations
import re
from src.delta.models import ChangeType, DocumentDelta, ElementDelta
from src.grounded_chat.models import (
    ChangeEvidence,
    GroundedChatResponse,
)


class GroundedChatService:

    def answer(
        self,
        *,
        question: str,
        delta: DocumentDelta,
    ) -> GroundedChatResponse:
        normalized_question = question.strip().lower()

        relevant_changes = [
            change
            for change in delta.changes
            if change.significant
            and change.change_type != ChangeType.UNCHANGED
            and self._is_relevant(
                normalized_question,
                change,
            )
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
            for change in relevant_changes[:10]
        ]

        answer = self._build_answer(
            question=question,
            evidence=evidence,
        )

        return GroundedChatResponse(
            answer=answer,
            evidence=evidence,
            grounded=True,
        )

    @staticmethod
    def _is_relevant(
        question: str,
        change: ElementDelta,
    ) -> bool:
        question_terms = {
            term
            for term in re.findall(
                r"[A-Z0-9]+",
                question.upper(),
            )
    if len(term) >= 3
}
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

        change_text = (
            f"{before_content} {after_content}"
        ).upper()

        return any(
            term in change_text
            for term in question_terms
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
            f"Based on the detected revision changes for "
            f"the question '{question}':"
        ]

        for index, item in enumerate(
            evidence,
            start=1,
        ):
            before = item.before_content or "not present"
            after = item.after_content or "not present"

            lines.append(
                f"[{index}] {item.change_type.value}: "
                f"'{before}' → '{after}'"
            )

        return "\n".join(lines)