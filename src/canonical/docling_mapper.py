from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from typing import Any

from docling_core.types.doc.document import DoclingDocument

from src.canonical.model import (
    BoundingBox,
    CanonicalDocument,
    CanonicalPage,
    DocumentElement,
    DocumentFormat,
    ElementType,
)


class DoclingCanonicalMapper:
    

    def map_document(
        self,
        *,
        docling_document: DoclingDocument,
        document_id: str,
        source_path: str,
        document_format: DocumentFormat,
        metadata: dict[str, Any] | None = None,
    ) -> CanonicalDocument:
        normalized_document_id = document_id.strip()

        if not normalized_document_id:
            raise ValueError("document_id must not be empty")

        if not docling_document.pages:
            raise ValueError(
                f"Docling document '{normalized_document_id}' has no pages"
            )

        page_elements: dict[int, list[DocumentElement]] = defaultdict(list)
        seen_element_ids: set[str] = set()

        for item, hierarchy_level in docling_document.iterate_items():
            text = self._extract_text(item)

            if not text:
                continue

            provenance_entries = getattr(item, "prov", None) or []

            # Items without provenance cannot be grounded to a page and
            # therefore should not become spatial canonical elements.
            if not provenance_entries:
                continue

            for provenance_index, provenance in enumerate(
                provenance_entries
            ):
                page_number = int(provenance.page_no)
                docling_page = docling_document.pages.get(page_number)

                if docling_page is None:
                    continue

                docling_bbox = getattr(provenance, "bbox", None)

                if docling_bbox is None:
                    continue

                page_width = float(docling_page.size.width)
                page_height = float(docling_page.size.height)

                canonical_bbox = self._map_bounding_box(
                    docling_bbox=docling_bbox,
                    page_width=page_width,
                    page_height=page_height,
                )

                element_type = self._map_element_type(
                    label=getattr(item, "label", None),
                    text=text,
                )

                element_id = self._create_element_id(
                    document_id=normalized_document_id,
                    page_number=page_number,
                    text=text,
                    bounding_box=canonical_bbox,
                    provenance_index=provenance_index,
                )

                # Avoid inserting the same grounded element more than once.
                if element_id in seen_element_ids:
                    continue

                seen_element_ids.add(element_id)

                charspan = getattr(provenance, "charspan", None)

                element_metadata: dict[str, Any] = {
                    "docling_item_type": type(item).__name__,
                    "docling_label": self._label_value(
                        getattr(item, "label", None)
                    ),
                    "hierarchy_level": hierarchy_level,
                    "provenance_index": provenance_index,
                    "coordinate_system": "normalized_top_left",
                }

                if charspan is not None:
                    element_metadata["charspan"] = list(charspan)

                page_elements[page_number].append(
                    DocumentElement(
                        element_id=element_id,
                        element_type=element_type,
                        text=text,
                        bbox=canonical_bbox,
                        metadata=element_metadata,
                    )
                )

        canonical_pages: list[CanonicalPage] = []

        for page_number, docling_page in sorted(
            docling_document.pages.items(),
            key=lambda entry: entry[0],
        ):
            elements = page_elements.get(page_number, [])

            # Top-to-bottom and then left-to-right ordering provides
            # deterministic output for reports, tests and comparisons.
            elements.sort(
                key=lambda element: (
                    element.bbox.y0,
                    element.bbox.x0,
                    element.bbox.y1,
                    element.bbox.x1,
                    element.element_id,
                )
            )

            canonical_pages.append(
                CanonicalPage(
                    page_number=int(page_number),
                    width=float(docling_page.size.width),
                    height=float(docling_page.size.height),
                    elements=elements,
                )
            )

        document_metadata = dict(metadata or {})
        document_metadata.update(
            {
                "parser": "docling",
                "source_path": source_path,
                "coordinate_system": "normalized_top_left",
            }
        )

        return CanonicalDocument(
            pid=normalized_document_id,
            source_format=document_format,
            pages=canonical_pages,
            metadata=document_metadata,
        )

    @staticmethod
    def _extract_text(item: Any) -> str | None:
        """
        Extract and normalize textual content from a Docling item.
        """

        raw_text = getattr(item, "text", None)

        if not isinstance(raw_text, str):
            return None

        normalized_text = " ".join(raw_text.split())

        return normalized_text or None

    @staticmethod
    def _map_bounding_box(
        *,
        docling_bbox: Any,
        page_width: float,
        page_height: float,
    ) -> BoundingBox:
        """
        Convert a Docling bounding box into normalized top-left coordinates.

        The returned coordinates are between 0 and 1, making spatial
        comparison independent of the source page dimensions.
        """

        if page_width <= 0:
            raise ValueError("page_width must be positive")

        if page_height <= 0:
            raise ValueError("page_height must be positive")

        top_left_bbox = docling_bbox.to_top_left_origin(page_height)

        x0 = DoclingCanonicalMapper._clamp(
            float(top_left_bbox.l) / page_width
        )
        y0 = DoclingCanonicalMapper._clamp(
            float(top_left_bbox.t) / page_height
        )
        x1 = DoclingCanonicalMapper._clamp(
            float(top_left_bbox.r) / page_width
        )
        y1 = DoclingCanonicalMapper._clamp(
            float(top_left_bbox.b) / page_height
        )

        return BoundingBox(
            x0=min(x0, x1),
            y0=min(y0, y1),
            x1=max(x0, x1),
            y1=max(y0, y1),
        )

    @staticmethod
    def _map_element_type(
        *,
        label: Any,
        text: str,
    ) -> ElementType:
        label_value = DoclingCanonicalMapper._label_value(label)
        normalized_text = text.strip().upper()

        if label_value in {
            "table",
            "table_cell",
        }:
            return ElementType.TABLE_CELL

        if label_value in {
            "picture",
            "image",
        }:
            return ElementType.IMAGE

        if label_value in {
            "note",
            "footnote",
        }:
            return ElementType.NOTE

        if (
            normalized_text.startswith("NOTE ")
            or normalized_text.startswith("NOTE:")
            or normalized_text.startswith("NOTES:")
        ):
            return ElementType.NOTE

        if DoclingCanonicalMapper._looks_like_dimension(
            normalized_text
        ):
            return ElementType.DIMENSION

        return ElementType.TEXT

    @staticmethod
    def _looks_like_dimension(text: str) -> bool:
        """
        Detect engineering measurements without classifying ordinary
        words containing unit-like letter sequences.
        """

        dimension_pattern = re.compile(
            r"""
            (?<![A-Z0-9])
            [-+]?
            \d+(?:\.\d+)?
            \s*
            (?:
                MM
                |CM
                |M
                |IN
                |INCH
                |BAR
                |BARG
                |KPA
                |MPA
                |KG/H
                |KW
                |°C
                |DEG(?:REE)?S?
            )
            (?![A-Z0-9])
            """,
            re.IGNORECASE | re.VERBOSE,
        )

        return bool(dimension_pattern.search(text))

    @staticmethod
    def _create_element_id(
        *,
        document_id: str,
        page_number: int,
        text: str,
        bounding_box: BoundingBox,
        provenance_index: int,
    ) -> str:
        """
        Create a deterministic ID from stable element attributes.
        """

        identity = "|".join(
            [
                document_id,
                str(page_number),
                text,
                f"{bounding_box.x0:.6f}",
                f"{bounding_box.y0:.6f}",
                f"{bounding_box.x1:.6f}",
                f"{bounding_box.y1:.6f}",
                str(provenance_index),
            ]
        )

        digest = hashlib.sha256(
            identity.encode("utf-8")
        ).hexdigest()[:16]

        return f"element-{digest}"

    @staticmethod
    def _label_value(label: Any) -> str | None:
        if label is None:
            return None

        value = getattr(label, "value", label)

        return str(value).strip().lower()

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))