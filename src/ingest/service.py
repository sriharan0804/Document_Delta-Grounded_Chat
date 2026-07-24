from __future__ import annotations

from src.canonical.model import CanonicalDocument
from src.ingest.base import FormatAdapter, UnsupportedFormatError
from src.ingest.resolver import PIDResolver


class IngestionService:
    

    def __init__(
        self,
        resolver: PIDResolver,
        adapters: list[FormatAdapter],
    ) -> None:
        if not adapters:
            raise ValueError(
                "At least one format adapter must be registered"
            )

        self._resolver = resolver
        self._adapters = adapters

    def ingest(self, pid: str) -> CanonicalDocument:
        source = self._resolver.resolve(pid)

        for adapter in self._adapters:
            if adapter.supports(source):
                return adapter.ingest(source)

        raise UnsupportedFormatError(
            f"No adapter supports PID '{pid}' "
            f"with extension '{source.extension}'"
        )