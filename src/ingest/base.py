from __future__ import annotations

from abc import ABC, abstractmethod

from src.canonical.model import CanonicalDocument, DocumentFormat
from src.ingest.source import DocumentSource


class UnsupportedFormatError(ValueError):
    """Raised when no ingestion adapter supports a document."""

   
class FormatAdapter(ABC):
    

    @property
    @abstractmethod
    def document_format(self) -> DocumentFormat:
        raise NotImplementedError

    @abstractmethod
    def supports(self, source: DocumentSource) -> bool:
        
        raise NotImplementedError

    @abstractmethod
    def ingest(
        self,
        source: DocumentSource,
    ) -> CanonicalDocument:
        
        raise NotImplementedError