from __future__ import annotations

import hashlib

import fitz

from src.canonical.model import (
    BoundingBox,
    CanonicalDocument,
    CanonicalPage,
    DocumentElement,
    DocumentFormat,
    ElementType,
)
from src.ingest.base import FormatAdapter
from src.ingest.source import DocumentSource


class NativePDFAdapter(FormatAdapter):
    

    @property
    def document_format(self) -> DocumentFormat:
        return DocumentFormat.NATIVE_PDF

    def supports(self, source: DocumentSource) -> bool:
        if source.extension != ".pdf":
            return False

        try:
            pdf = fitz.open(
                stream=source.read_bytes(),
                filetype="pdf",
            )
        except Exception:
            return False

        try:
            for page in pdf:
                if page.get_text().strip():
                    return True

            return False
        finally:
            pdf.close()

    def ingest(
        self,
        source: DocumentSource,
    ) -> CanonicalDocument:
        pdf_bytes = source.read_bytes()

        try:
            pdf = fitz.open(
                stream=pdf_bytes,
                filetype="pdf",
            )
        except Exception as exc:
            raise ValueError(
                f"Unable to open PDF for PID '{source.pid}'"
            ) from exc

        try:
            pages = [
                self._extract_page(
                    pid=source.pid,
                    page=page,
                )
                for page in pdf
            ]

            return CanonicalDocument(
                pid=source.pid,
                revision=source.revision,
                source_format=self.document_format,
                filename=source.filename,
                pages=pages,
                metadata={
                    **source.metadata,
                    "pdf_page_count": pdf.page_count,
                    "adapter": self.__class__.__name__,
                },
            )
        finally:
            pdf.close()

    def _extract_page(
        self,
        pid: str,
        page: fitz.Page,
    ) -> CanonicalPage:
        elements: list[DocumentElement] = []

        blocks = page.get_text(
            "blocks",
            sort=True,
        )

        for block_index, block in enumerate(blocks):
            element = self._block_to_element(
                pid=pid,
                page_number=page.number + 1,
                block_index=block_index,
                block=block,
            )

            if element is not None:
                elements.append(element)

        return CanonicalPage(
            page_number=page.number + 1,
            width=float(page.rect.width),
            height=float(page.rect.height),
            elements=elements,
            metadata={
                "rotation": page.rotation,
            },
        )

    def _block_to_element(
        self,
        pid: str,
        page_number: int,
        block_index: int,
        block: tuple,
    ) -> DocumentElement | None:
        x0, y0, x1, y1, text, block_number, block_type = block[:7]

        cleaned_text = self._clean_text(text)

        if not cleaned_text:
            return None

        element_type = self._classify_element_type(cleaned_text)

        element_id = self._build_element_id(
            pid=pid,
            page_number=page_number,
            block_index=block_index,
            content=cleaned_text,
        )

        return DocumentElement(
            element_id=element_id,
            element_type=element_type,
            content=cleaned_text,
            bbox=BoundingBox(
                x0=max(0.0, float(x0)),
                y0=max(0.0, float(y0)),
                x1=max(0.0, float(x1)),
                y1=max(0.0, float(y1)),
            ),
            confidence=1.0,
            metadata={
                "block_number": block_number,
                "block_type": block_type,
                "extraction_method": "pymupdf_text_layer",
            },
        )

    @staticmethod
    def _clean_text(text: str) -> str:
        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        return " ".join(lines)

    @staticmethod
    def _classify_element_type(
        content: str,
    ) -> ElementType:
        normalized = content.strip().lower()

        if NativePDFAdapter._looks_like_dimension(normalized):
            return ElementType.DIMENSION

        if normalized.startswith(
            (
                "note:",
                "notes:",
                "general note",
                "general notes",
            )
        ):
            return ElementType.NOTE

        return ElementType.TEXT

    @staticmethod
    def _looks_like_dimension(content: str) -> bool:
        dimension_markers = (
            " mm",
            " cm",
            " m",
            " inch",
            " inches",
            " ft",
            "°",
            "±",
            "diameter",
            "radius",
            "ø",
        )

        contains_digit = any(
            character.isdigit()
            for character in content
        )

        contains_marker = any(
            marker in content
            for marker in dimension_markers
        )

        return contains_digit and contains_marker

    @staticmethod
    def _build_element_id(
        pid: str,
        page_number: int,
        block_index: int,
        content: str,
    ) -> str:
        raw_value = (
            f"{pid}|{page_number}|{block_index}|{content}"
        )

        digest = hashlib.sha256(
            raw_value.encode("utf-8")
        ).hexdigest()[:12]

        return f"{pid}-p{page_number}-b{block_index}-{digest}"