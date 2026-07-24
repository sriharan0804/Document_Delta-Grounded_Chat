from __future__ import annotations

import json
from pathlib import Path

from src.canonical.model import CanonicalDocument


def export_canonical_json(
    document: CanonicalDocument,
    output_path: str | Path,
) -> Path:
    

    destination = Path(output_path)

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    document_data = document.model_dump(
        mode="json",
    )

    destination.write_text(
        json.dumps(
            document_data,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return destination


def build_canonical_summary(
    document: CanonicalDocument,
) -> dict[str, object]:
    
    element_type_counts: dict[str, int] = {}

    for page in document.pages:
        for element in page.elements:
            element_type = element.element_type.value

            element_type_counts[element_type] = (
                element_type_counts.get(element_type, 0) + 1
            )

    return {
        "pid": document.pid,
        "revision": document.revision,
        "source_format": document.source_format.value,
        "filename": document.filename,
        "page_count": document.page_count,
        "element_count": document.element_count,
        "element_type_counts": element_type_counts,
    }