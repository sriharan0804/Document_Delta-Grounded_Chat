from __future__ import annotations

from docling_core.types.doc.base import (
    BoundingBox as DoclingBoundingBox,
    CoordOrigin,
)

from src.canonical.docling_mapper import (
    DoclingCanonicalMapper,
)
from src.canonical.model import ElementType


def test_maps_top_left_bounding_box_to_normalized_coordinates():
    docling_bbox = DoclingBoundingBox(
        l=100,
        t=200,
        r=300,
        b=400,
        coord_origin=CoordOrigin.TOPLEFT,
    )

    result = DoclingCanonicalMapper._map_bounding_box(
        docling_bbox=docling_bbox,
        page_width=1000,
        page_height=2000,
    )

    assert result.x0 == 0.1
    assert result.y0 == 0.1
    assert result.x1 == 0.3
    assert result.y1 == 0.2


def test_maps_bottom_left_bbox_to_top_left_coordinates():
    docling_bbox = DoclingBoundingBox(
        l=100,
        t=1800,
        r=300,
        b=1600,
        coord_origin=CoordOrigin.BOTTOMLEFT,
    )

    result = DoclingCanonicalMapper._map_bounding_box(
        docling_bbox=docling_bbox,
        page_width=1000,
        page_height=2000,
    )

    assert result.x0 == 0.1
    assert result.y0 == 0.1
    assert result.x1 == 0.3
    assert result.y1 == 0.2


def test_note_prefix_maps_to_note_type():
    result = DoclingCanonicalMapper._map_element_type(
        label="text",
        text="NOTE 19",
    )

    assert result == ElementType.NOTE


def test_dimension_text_maps_to_dimension_type():
    result = DoclingCanonicalMapper._map_element_type(
        label="text",
        text="DESIGN PRESSURE 286 BARG",
    )

    assert result == ElementType.DIMENSION


def test_regular_text_maps_to_text_type():
    result = DoclingCanonicalMapper._map_element_type(
        label="text",
        text="COMPRESSOR DISCHARGE",
    )

    assert result == ElementType.TEXT


def test_element_id_is_deterministic():
    bbox = DoclingCanonicalMapper._map_bounding_box(
        docling_bbox=DoclingBoundingBox(
            l=10,
            t=20,
            r=30,
            b=40,
            coord_origin=CoordOrigin.TOPLEFT,
        ),
        page_width=100,
        page_height=100,
    )

    first = DoclingCanonicalMapper._create_element_id(
        document_id="revision-a",
        page_number=1,
        text="COMPRESSOR",
        bounding_box=bbox,
        provenance_index=0,
    )

    second = DoclingCanonicalMapper._create_element_id(
        document_id="revision-a",
        page_number=1,
        text="COMPRESSOR",
        bounding_box=bbox,
        provenance_index=0,
    )

    assert first == second
    assert first.startswith("element-")