from __future__ import annotations

from src.canonical.model import (
    BoundingBox,
    CanonicalDocument,
    DocumentElement,
)
from src.delta.models import (
    ChangeType,
    DeltaSummary,
    DocumentAlignment,
    DocumentDelta,
    ElementDelta,
    ElementMatch,
)


class ChangeClassificationService:
    

    def __init__(
        self,
        *,
        movement_threshold: float = 0.015,
    ) -> None:
        if not 0.0 <= movement_threshold <= 1.0:
            raise ValueError(
                "movement_threshold must be between 0 and 1"
            )

        self._movement_threshold = movement_threshold

    def classify_documents(
        self,
        *,
        before: CanonicalDocument,
        after: CanonicalDocument,
        alignment: DocumentAlignment,
    ) -> DocumentDelta:
        changes: list[ElementDelta] = []

        for match in alignment.matches:
            changes.append(
                self._classify_match(match)
            )

        for removed_element in alignment.unmatched_before:
            changes.append(
                ElementDelta(
                    change_type=ChangeType.REMOVED,
                    before=removed_element,
                    after=None,
                    match_score=None,
                    text_changed=False,
                    position_changed=False,
                )
            )

        for added_element in alignment.unmatched_after:
            changes.append(
                ElementDelta(
                    change_type=ChangeType.ADDED,
                    before=None,
                    after=added_element,
                    match_score=None,
                    text_changed=False,
                    position_changed=False,
                )
            )

        changes.sort(key=self._change_sort_key)

        summary = self._build_summary(changes)

        return DocumentDelta(
            before_pid=before.pid,
            after_pid=after.pid,
            changes=changes,
            summary=summary,
        )

    def _classify_match(
        self,
        match: ElementMatch,
    ) -> ElementDelta:
        text_changed = not self._same_text(
            match.before,
            match.after,
        )

        position_changed = self._position_changed(
            match.before.bbox,
            match.after.bbox,
        )

        if text_changed and position_changed:
            change_type = ChangeType.MOVED_AND_MODIFIED

        elif text_changed:
            change_type = ChangeType.MODIFIED

        elif position_changed:
            change_type = ChangeType.MOVED

        else:
            change_type = ChangeType.UNCHANGED

        return ElementDelta(
            change_type=change_type,
            before=match.before,
            after=match.after,
            match_score=match.score,
            text_changed=text_changed,
            position_changed=position_changed,
        )

    @staticmethod
    def _same_text(
        before: DocumentElement,
        after: DocumentElement,
    ) -> bool:
        before_text = " ".join(
            before.content.upper().split()
        )

        after_text = " ".join(
            after.content.upper().split()
        )

        return before_text == after_text

    def _position_changed(
        self,
        before: BoundingBox,
        after: BoundingBox,
    ) -> bool:
        before_center_x = (
            before.x0 + before.x1
        ) / 2

        before_center_y = (
            before.y0 + before.y1
        ) / 2

        after_center_x = (
            after.x0 + after.x1
        ) / 2

        after_center_y = (
            after.y0 + after.y1
        ) / 2

        horizontal_movement = abs(
            before_center_x - after_center_x
        )

        vertical_movement = abs(
            before_center_y - after_center_y
        )

        maximum_movement = max(
            horizontal_movement,
            vertical_movement,
        )

        return maximum_movement > self._movement_threshold

    @staticmethod
    def _build_summary(
        changes: list[ElementDelta],
    ) -> DeltaSummary:
        counts = {
            change_type: 0
            for change_type in ChangeType
        }

        for change in changes:
            counts[change.change_type] += 1

        return DeltaSummary(
            unchanged=counts[ChangeType.UNCHANGED],
            added=counts[ChangeType.ADDED],
            removed=counts[ChangeType.REMOVED],
            modified=counts[ChangeType.MODIFIED],
            moved=counts[ChangeType.MOVED],
            moved_and_modified=counts[
                ChangeType.MOVED_AND_MODIFIED
            ],
        )

    @staticmethod
    def _change_sort_key(
        change: ElementDelta,
    ) -> tuple[str, str]:
        element = change.after or change.before

        element_id = (
            element.element_id
            if element is not None
            else ""
        )

        return (
            change.change_type.value,
            element_id,
        )