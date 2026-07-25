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


class ChatAskRequest(BaseModel):
    
    report_id: str = Field(
        min_length=1,
        description="Identifier of an existing delta report.",
    )
    question: str = Field(
        min_length=2,
        max_length=1000,
        description="Question to answer using the selected report.",
    )
    max_evidence: int = Field(
        default=8,
        ge=1,
        le=20,
        description="Maximum number of evidence items to retrieve.",
    )


class ChatCitation(BaseModel):
   
    evidence_id: str
    change_type: str
    content: str
    before_content: str | None = None
    after_content: str | None = None
    element_type: str | None = None
    score: float


class ChatAskResponse(BaseModel):
    
    success: bool = True
    report_id: str
    question: str
    answer: str
    grounded: bool
    evidence_count: int
    citations: list[ChatCitation]