from __future__ import annotations

from pydantic import BaseModel, Field


class ExpectedChange(BaseModel):
    

    change_id: str
    change_type: str
    before_content: str | None = None
    after_content: str | None = None
    page_number: int | None = None


class ChatEvaluationCase(BaseModel):
    

    case_id: str
    question: str
    expected_grounded: bool
    expected_terms: list[str] = Field(
        default_factory=list
    )
    expected_citation_terms: list[str] = Field(
        default_factory=list
    )


class EvaluationDataset(BaseModel):
    

    dataset_id: str
    description: str
    before_pid: str
    after_pid: str
    expected_changes: list[ExpectedChange] = Field(
        default_factory=list
    )
    chat_cases: list[ChatEvaluationCase] = Field(
        default_factory=list
    )

class EvaluationScope(BaseModel):
    

    content_terms: list[str] = Field(
        default_factory=list
    )

    page_numbers: list[int] = Field(
        default_factory=list
    )


class EvaluationDataset(BaseModel):
    

    dataset_id: str
    description: str
    before_pid: str
    after_pid: str

    evaluation_scope: EvaluationScope | None = None

    expected_changes: list[ExpectedChange] = Field(
        default_factory=list
    )

    chat_cases: list[ChatEvaluationCase] = Field(
        default_factory=list
    )