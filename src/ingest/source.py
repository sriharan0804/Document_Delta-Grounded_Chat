from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class DocumentSource(BaseModel):
  

    pid: str = Field(min_length=1)
    file_path: Path
    revision: str | None = None
    filename: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)

    @property
    def extension(self) -> str:
        return self.file_path.suffix.lower()

    def read_bytes(self) -> bytes:
        if not self.file_path.exists():
            raise FileNotFoundError(
                f"Document file does not exist: {self.file_path}"
            )

        if not self.file_path.is_file():
            raise ValueError(
                f"Document path is not a file: {self.file_path}"
            )

        return self.file_path.read_bytes()