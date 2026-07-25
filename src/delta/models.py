from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from src.canonical.model import DocumentElement


class ChangeType(str, Enum):
    

    UNCHANGED = "unchanged"
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    MOVED = "moved"
    MOVED_AND_MODIFIED = "moved_and_modified"


class MatchScore(BaseModel):
    

    text_similarity: float = Field(ge=0.0, le=1.0)
    spatial_similarity: float = Field(ge=0.0, le=1.0)
    type_similarity: float = Field(ge=0.0, le=1.0)
    total_score: float = Field(ge=0.0, le=1.0)


class ElementMatch(BaseModel):
    

    before: DocumentElement
    after: DocumentElement
    score: MatchScore


class DocumentAlignment(BaseModel):
    

    matches: list[ElementMatch] = Field(default_factory=list)

    unmatched_before: list[DocumentElement] = Field(
        default_factory=list
    )

    unmatched_after: list[DocumentElement] = Field(
        default_factory=list
    )

    @property
    def match_count(self) -> int:
        return len(self.matches)

    @property
    def removed_count(self) -> int:
        return len(self.unmatched_before)

    @property
    def added_count(self) -> int:
        return len(self.unmatched_after)



class ElementDelta(BaseModel):
    

    change_type: ChangeType

    before: DocumentElement | None = None
    after: DocumentElement | None = None

    match_score: MatchScore | None = None

    text_changed: bool = False
    position_changed: bool = False

    significant: bool = True
    significance_reason: str | None = None


class DeltaSummary(BaseModel):
   

    unchanged: int = 0
    added: int = 0
    removed: int = 0
    modified: int = 0
    moved: int = 0
    moved_and_modified: int = 0

    @property
    def total_changes(self) -> int:
        return (
            self.added
            + self.removed
            + self.modified
            + self.moved
            + self.moved_and_modified
        )


class DocumentDelta(BaseModel):
   

    before_pid: str
    after_pid: str

    changes: list[ElementDelta] = Field(default_factory=list)

    summary: DeltaSummary

    @property
    def changed_elements(self) -> list[ElementDelta]:
        return [
            change
            for change in self.changes
            if change.change_type != ChangeType.UNCHANGED
        ]