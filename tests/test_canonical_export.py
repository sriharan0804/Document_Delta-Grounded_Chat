import json
from pathlib import Path

from src.canonical.export import (
    build_canonical_summary,
    export_canonical_json,
)
from src.canonical.model import (
    BoundingBox,
    CanonicalDocument,
    CanonicalPage,
    DocumentElement,
    DocumentFormat,
    ElementType,
)


def build_sample_document() -> CanonicalDocument:
    return CanonicalDocument(
        pid="PID-A",
        revision="A",
        source_format=DocumentFormat.NATIVE_PDF,
        filename="revision-a.pdf",
        pages=[
            CanonicalPage(
                page_number=1,
                width=612,
                height=792,
                elements=[
                    DocumentElement(
                        element_id="element-1",
                        element_type=ElementType.TEXT,
                        content="Pump specification",
                        bbox=BoundingBox(
                            x0=72,
                            y0=60,
                            x1=180,
                            y1=80,
                        ),
                    ),
                    DocumentElement(
                        element_id="element-2",
                        element_type=ElementType.DIMENSION,
                        content="Maximum pressure: 10 bar",
                        bbox=BoundingBox(
                            x0=72,
                            y0=100,
                            x1=240,
                            y1=120,
                        ),
                    ),
                ],
            )
        ],
    )


def test_export_canonical_json(
    tmp_path: Path,
) -> None:
    document = build_sample_document()
    output_path = tmp_path / "nested" / "canonical.json"

    result_path = export_canonical_json(
        document=document,
        output_path=output_path,
    )

    assert result_path == output_path
    assert output_path.exists()

    exported_data = json.loads(
        output_path.read_text(encoding="utf-8")
    )

    assert exported_data["pid"] == "PID-A"
    assert exported_data["revision"] == "A"
    assert exported_data["source_format"] == "native_pdf"
    assert len(exported_data["pages"]) == 1


def test_build_canonical_summary() -> None:
    document = build_sample_document()

    summary = build_canonical_summary(document)

    assert summary["pid"] == "PID-A"
    assert summary["page_count"] == 1
    assert summary["element_count"] == 2
    assert summary["element_type_counts"] == {
        "text": 1,
        "dimension": 1,
    }