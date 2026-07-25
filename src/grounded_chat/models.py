from __future__ import annotations

from pydantic import BaseModel, Field

from src.delta.models import ChangeType


class GroundedChatRequest(BaseModel):
    question: str = Field(min_length=1)


class ChangeEvidence(BaseModel):
    change_type: ChangeType
    before_content: str | None = None
    after_content: str | None = None
    before_element_id: str | None = None
    after_element_id: str | None = None
    significant: bool = True


class GroundedChatResponse(BaseModel):
    answer: str
    evidence: list[ChangeEvidence] = Field(default_factory=list)
    grounded: bool