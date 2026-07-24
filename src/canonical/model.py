from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class DocumentFormat(str, Enum):


    NATIVE_PDF = "native_pdf"
    SCANNED_PDF = "scanned_pdf"
    DWG = "dwg"


class ElementType(str, Enum):
  

    TEXT = "text"
    NOTE = "note"
    DIMENSION = "dimension"
    TABLE_CELL = "table_cell"
    GEOMETRY = "geometry"
    IMAGE = "image"
    UNKNOWN = "unknown"


class BoundingBox(BaseModel):
    

    x0: float = Field(ge=0)
    y0: float = Field(ge=0)
    x1: float = Field(ge=0)
    y1: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_coordinates(self) -> "BoundingBox":
        if self.x1 < self.x0:
            raise ValueError("x1 must be greater than or equal to x0")

        if self.y1 < self.y0:
            raise ValueError("y1 must be greater than or equal to y0")

        return self

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0


class DocumentElement(BaseModel):
    

    element_id: str = Field(min_length=1)
    element_type: ElementType
    content: str = ""
    bbox: BoundingBox | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CanonicalPage(BaseModel):
    
    page_number: int = Field(ge=1)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    elements: list[DocumentElement] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CanonicalDocument(BaseModel):
    

    pid: str = Field(min_length=1)
    revision: str | None = None
    source_format: DocumentFormat
    filename: str | None = None
    pages: list[CanonicalPage] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def element_count(self) -> int:
        return sum(len(page.elements) for page in self.pages)

    def get_element(self, element_id: str) -> DocumentElement | None:
        for page in self.pages:
            for element in page.elements:
                if element.element_id == element_id:
                    return element

        return None