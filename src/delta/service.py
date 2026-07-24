from __future__ import annotations

from src.canonical.model import CanonicalDocument
from src.delta.alignment import ElementAlignmentService
from src.delta.classifier import ChangeClassificationService
from src.delta.models import DocumentDelta


class DocumentDeltaService:
   

    def __init__(
        self,
        *,
        alignment_service: ElementAlignmentService | None = None,
        classification_service: (
            ChangeClassificationService | None
        ) = None,
    ) -> None:
        self._alignment_service = (
            alignment_service
            or ElementAlignmentService()
        )

        self._classification_service = (
            classification_service
            or ChangeClassificationService()
        )

    def compare(
        self,
        *,
        before: CanonicalDocument,
        after: CanonicalDocument,
    ) -> DocumentDelta:
        alignment = self._alignment_service.align_documents(
            before,
            after,
        )

        return self._classification_service.classify(
            before_pid=before.pid,
            after_pid=after.pid,
            alignment=alignment,
        )