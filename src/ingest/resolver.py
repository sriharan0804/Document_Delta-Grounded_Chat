from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from src.ingest.source import DocumentSource
from pydantic import BaseModel, Field


class LocalDocumentConfig(BaseModel):
    

    file_path: Path
    revision: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)



class PIDResolver(ABC):
   

    @abstractmethod
    def resolve(self, pid: str) -> DocumentSource:
        raise NotImplementedError


class LocalPIDResolver(PIDResolver):
   

    def __init__(
        self,
        pid_map: dict[str, DocumentSource],
    ) -> None:
        self._pid_map = pid_map

    def resolve(self, pid: str) -> DocumentSource:
        source = self._pid_map.get(pid)

        if source is None:
            raise KeyError(f"Unknown PID: {pid}")

        if not source.file_path.exists():
            raise FileNotFoundError(
                f"File for PID '{pid}' was not found: "
                f"{source.file_path}"
            )

        return source


def build_local_resolver(
    documents: dict[
        str,
        str | Path | LocalDocumentConfig,
    ],
) -> LocalPIDResolver:
    

    sources: dict[str, DocumentSource] = {}

    for pid, configuration in documents.items():
        if isinstance(configuration, LocalDocumentConfig):
            file_path = configuration.file_path
            revision = configuration.revision
            metadata = configuration.metadata
        else:
            file_path = Path(configuration)
            revision = None
            metadata = {}

        sources[pid] = DocumentSource(
            pid=pid,
            file_path=file_path,
            filename=file_path.name,
            revision=revision,
            metadata=metadata,
        )

    return LocalPIDResolver(sources)