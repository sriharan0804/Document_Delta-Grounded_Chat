from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str


class DeltaSummary(BaseModel):
    total_changes: int = 0
    added: int = 0
    removed: int = 0
    modified: int = 0
    moved: int = 0
    moved_and_modified: int = 0
    unchanged: int = 0


class DeltaCompareResponse(BaseModel):
    success: bool
    report_id: str
    report_path: str
    summary: DeltaSummary
    changes: list[dict[str, Any]] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    detail: str