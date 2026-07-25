from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SUPPORTED_CHANGE_TYPES = {
    "added",
    "removed",
    "modified",
    "moved",
    "moved_and_modified",
}


@dataclass(frozen=True)
class RetrievedEvidence:
    """A relevant delta-report change selected for answering a question."""

    evidence_id: str
    change_type: str
    before_content: str | None
    after_content: str | None
    score: float
    element_type: str | None = None

    @property
    def display_content(self) -> str:
        """Return the most useful text representation of the evidence."""

        if self.change_type == "removed":
            return self.before_content or ""

        if self.change_type == "modified":
            before = self.before_content or "unknown"
            after = self.after_content or "unknown"
            return f"{before} → {after}"

        if self.change_type == "moved_and_modified":
            before = self.before_content or "unknown"
            after = self.after_content or "unknown"
            return f"{before} → {after}"

        return self.after_content or self.before_content or ""


class GroundedChatService:
    

    _STOPWORDS = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "been",
        "between",
        "by",
        "change",
        "changed",
        "changes",
        "did",
        "document",
        "for",
        "from",
        "has",
        "have",
        "how",
        "in",
        "is",
        "it",
        "me",
        "of",
        "on",
        "or",
        "report",
        "show",
        "that",
        "the",
        "there",
        "this",
        "to",
        "was",
        "were",
        "what",
        "which",
        "with",
    }

    _CHANGE_TYPE_KEYWORDS = {
        "added": {"add", "added", "addition", "additions", "new", "introduced"},
        "removed": {
            "remove",
            "removed",
            "removal",
            "removals",
            "delete",
            "deleted",
            "missing",
        },
        "modified": {
            "modify",
            "modified",
            "modification",
            "modifications",
            "updated",
            "revised",
            "text",
        },
        "moved": {
            "move",
            "moved",
            "movement",
            "position",
            "relocated",
            "location",
        },
        "moved_and_modified": {
            "moved-and-modified",
            "moved_and_modified",
            "relocated-and-updated",
        },
    }
    _DOMAIN_ALIASES = {
        "valve": {
            "valve",
            "fv",
            "xv",
            "hv",
            "lv",
            "pv",
            "tv",
            "mov",
        },
        "pressure": {
            "pressure",
            "psv",
            "pt",
            "pi",
            "pic",
        },
        "temperature": {
            "temperature",
            "tt",
            "ti",
            "tic",
        },
    }

    def __init__(
        self,
        *,
        max_evidence: int = 8,
        minimum_score: float = 0.01,
    ) -> None:
        if max_evidence < 1:
            raise ValueError("max_evidence must be at least 1")

        self.max_evidence = max_evidence
        self.minimum_score = minimum_score

    def answer(
        self,
        *,
        question: str,
        report: dict[str, Any],
    ) -> dict[str, Any]:
        

        normalized_question = question.strip()

        if not normalized_question:
            raise ValueError("Question cannot be empty.")

        changes = self._extract_changes(report)

        if not changes:
            return {
                "answer": (
                    "I could not find any reportable changes in this delta "
                    "report."
                ),
                "grounded": True,
                "citations": [],
                "evidence_count": 0,
            }

        requested_change_types = self._detect_requested_change_types(
            normalized_question
        )

        evidence = self._retrieve(
            question=normalized_question,
            changes=changes,
            requested_change_types=requested_change_types,
        )

        if not evidence:
            return {
                "answer": (
                    "I could not find evidence in the selected delta report "
                    "that answers this question."
                ),
                "grounded": True,
                "citations": [],
                "evidence_count": 0,
            }

        answer = self._build_answer(
            question=normalized_question,
            evidence=evidence,
            requested_change_types=requested_change_types,
        )

        citations = [
            {
                "evidence_id": item.evidence_id,
                "change_type": item.change_type,
                "content": item.display_content,
                "before_content": item.before_content,
                "after_content": item.after_content,
                "element_type": item.element_type,
                "score": round(item.score, 4),
            }
            for item in evidence
        ]

        return {
            "answer": answer,
            "grounded": True,
            "citations": citations,
            "evidence_count": len(citations),
        }

    def _extract_changes(
        self,
        report: dict[str, Any],
    ) -> list[dict[str, Any]]:
        changes = report.get("changes", [])

        if not isinstance(changes, list):
            raise ValueError("Delta report has an invalid 'changes' field.")

        return [
            change
            for change in changes
            if isinstance(change, dict)
            and change.get("change_type") in SUPPORTED_CHANGE_TYPES
            and change.get("significant", True)
        ]

    def _retrieve(
        self,
        *,
        question: str,
        changes: list[dict[str, Any]],
        requested_change_types: set[str],
    ) -> list[RetrievedEvidence]:
        query_tokens = self._tokenize(question)

        domain_tokens = self._expand_domain_tokens(
            self._extract_domain_tokens(question)
        )

        ranked: list[RetrievedEvidence] = []

        for index, change in enumerate(changes):
            change_type = str(
                change.get("change_type", "unknown")
            ).strip().lower()

            before = self._extract_content(change.get("before"))
            after = self._extract_content(change.get("after"))
            element_type = self._extract_element_type(change)

            searchable_text = " ".join(
                value
                for value in [
                    change_type.replace("_", " "),
                    element_type or "",
                    before or "",
                    after or "",
                ]
                if value
            )

            # This must be created before lexical_score or domain_score.
            document_tokens = self._tokenize(searchable_text)

            lexical_score = self._token_overlap_score(
                query_tokens=query_tokens,
                document_tokens=document_tokens,
            )

            domain_score = self._token_overlap_score(
                query_tokens=domain_tokens,
                document_tokens=document_tokens,
            )

            type_score = 0.0

            if requested_change_types:
                if change_type not in requested_change_types:
                    continue

                type_score = 2.0

                # For a specific question such as "What valves were added?",
                # reject added elements unrelated to valves.
                if domain_tokens and domain_score == 0:
                    continue

            exact_phrase_score = self._exact_phrase_score(
                question=question,
                searchable_text=searchable_text,
            )

            score = (
                type_score
                + lexical_score
                + (domain_score * 3.0)
                + exact_phrase_score
            )

            if score < self.minimum_score:
                continue

            evidence_id = self._build_evidence_id(
                change=change,
                fallback_index=index,
            )

            ranked.append(
                RetrievedEvidence(
                    evidence_id=evidence_id,
                    change_type=change_type,
                    before_content=before,
                    after_content=after,
                    score=score,
                    element_type=element_type,
                )
            )

        ranked.sort(
            key=lambda item: (
                -item.score,
                item.change_type,
                item.evidence_id,
            )
        )

        return ranked[: self.max_evidence]

        
    def _extract_domain_tokens(
        self,
        question: str,
    ) -> set[str]:
        tokens = self._tokenize(question)

        change_keywords = {
            self._normalize_token(keyword)
            for keywords in self._CHANGE_TYPE_KEYWORDS.values()
            for keyword in keywords
        }

        return tokens - change_keywords

    def _build_answer(
        self,
        *,
        question: str,
        evidence: list[RetrievedEvidence],
        requested_change_types: set[str],
    ) -> str:
        question_lower = question.lower()

        if self._is_count_question(question_lower):
            return self._build_count_answer(
                evidence=evidence,
                requested_change_types=requested_change_types,
            )

        grouped = Counter(item.change_type for item in evidence)

        if len(grouped) == 1:
            change_type = next(iter(grouped))
            heading = self._humanize_change_type(change_type)

            statements = [
                f'{index}. "{item.display_content}" [{item.evidence_id}]'
                for index, item in enumerate(evidence, start=1)
            ]

            return (
                f"I found {len(evidence)} relevant {heading.lower()} "
                f"{'change' if len(evidence) == 1 else 'changes'}:\n\n"
                + "\n".join(statements)
            )

        statements = [
            (
                f'{index}. {self._humanize_change_type(item.change_type)}: '
                f'"{item.display_content}" [{item.evidence_id}]'
            )
            for index, item in enumerate(evidence, start=1)
        ]

        return (
            f"I found {len(evidence)} relevant changes in the selected "
            "delta report:\n\n"
            + "\n".join(statements)
        )

    def _build_count_answer(
        self,
        *,
        evidence: list[RetrievedEvidence],
        requested_change_types: set[str],
    ) -> str:
        counts = Counter(item.change_type for item in evidence)

        if len(requested_change_types) == 1:
            requested_type = next(iter(requested_change_types))
            count = counts.get(requested_type, 0)

            return (
                f"I found {count} relevant "
                f"{self._humanize_change_type(requested_type).lower()} "
                f"{'change' if count == 1 else 'changes'} in the retrieved "
                "evidence."
            )

        parts = [
            f"{self._humanize_change_type(change_type)}: {count}"
            for change_type, count in sorted(counts.items())
        ]

        return "Relevant retrieved changes — " + ", ".join(parts) + "."

    def _detect_requested_change_types(self, question: str) -> set[str]:
        tokens = self._tokenize(question)
        question_lower = question.lower()
        detected: set[str] = set()

        for change_type, keywords in self._CHANGE_TYPE_KEYWORDS.items():
            if tokens.intersection(keywords):
                detected.add(change_type)

            if change_type in question_lower:
                detected.add(change_type)

        # "Moved and modified" is more specific than the separate categories.
        if (
            "moved" in detected
            and "modified" in detected
            and (
                "moved and modified" in question_lower
                or "moved_and_modified" in question_lower
            )
        ):
            detected.discard("moved")
            detected.discard("modified")
            detected.add("moved_and_modified")

        return detected

    def _tokenize(self, value: str) -> set[str]:
        raw_tokens = re.findall(
            r"[a-zA-Z0-9][a-zA-Z0-9_\-./\"]*",
            value.lower(),
        )

        normalized_tokens: set[str] = set()

        for token in raw_tokens:
            if token in self._STOPWORDS or len(token) <= 1:
                continue

            normalized_tokens.add(self._normalize_token(token))

        return normalized_tokens


    @staticmethod
    def _normalize_token(token: str) -> str:
        """Apply lightweight normalization for common plural forms."""

        if token.endswith("ves") and len(token) > 4:
            return token[:-1]

        if token.endswith("ies") and len(token) > 4:
            return token[:-3] + "y"

        if token.endswith("es") and len(token) > 4:
            return token[:-2]

        if token.endswith("s") and len(token) > 3:
            return token[:-1]

        return token

    @staticmethod
    def _token_overlap_score(
        *,
        query_tokens: set[str],
        document_tokens: set[str],
    ) -> float:
        if not query_tokens or not document_tokens:
            return 0.0

        overlap = query_tokens.intersection(document_tokens)

        if not overlap:
            return 0.0

        return len(overlap) / len(query_tokens)

    @staticmethod
    def _exact_phrase_score(
        *,
        question: str,
        searchable_text: str,
    ) -> float:
        searchable_lower = searchable_text.lower()

        quoted_phrases = re.findall(r'"([^"]+)"', question)

        if any(
            phrase.strip().lower() in searchable_lower
            for phrase in quoted_phrases
            if phrase.strip()
        ):
            return 3.0

        return 0.0

    def _expand_domain_tokens(
        self,
        tokens: set[str],
    ) -> set[str]:
        expanded = set(tokens)

        for token in tokens:
            expanded.update(
                self._DOMAIN_ALIASES.get(token, set())
            )

        return expanded
    def _extract_domain_tokens(
        self,
        question: str,
    ) -> set[str]:

        tokens = self._tokenize(question)

        change_keywords = {
            self._normalize_token(keyword)
            for keywords in self._CHANGE_TYPE_KEYWORDS.values()
            for keyword in keywords
        }

        return tokens - change_keywords

    @staticmethod
    def _extract_content(element: Any) -> str | None:
        if not isinstance(element, dict):
            return None

        content = element.get("content")

        if content is None:
            return None

        normalized = str(content).strip()
        return normalized or None

    @staticmethod
    def _extract_element_type(change: dict[str, Any]) -> str | None:
        for side in ("after", "before"):
            element = change.get(side)

            if isinstance(element, dict) and element.get("element_type"):
                return str(element["element_type"])

        return None

    @staticmethod
    def _build_evidence_id(
        *,
        change: dict[str, Any],
        fallback_index: int,
    ) -> str:
        for side in ("after", "before"):
            element = change.get(side)

            if isinstance(element, dict) and element.get("element_id"):
                return str(element["element_id"])

        return f"change-{fallback_index + 1:04d}"

    @staticmethod
    def _is_count_question(question: str) -> bool:
        return any(
            phrase in question
            for phrase in (
                "how many",
                "number of",
                "count of",
                "total",
            )
        )

    @staticmethod
    def _humanize_change_type(change_type: str) -> str:
        labels = {
            "added": "Added",
            "removed": "Removed",
            "modified": "Modified",
            "moved": "Moved",
            "moved_and_modified": "Moved and modified",
        }

        return labels.get(
            change_type,
            change_type.replace("_", " ").title(),
        )