from pathlib import Path

import fitz
import pytest


@pytest.fixture
def native_pdf_path(
    tmp_path: Path,
) -> Path:
    file_path = tmp_path / "revision-a.pdf"

    pdf = fitz.open()
    page = pdf.new_page(
        width=612,
        height=792,
    )

    page.insert_text(
        (72, 72),
        "Pump specification",
        fontsize=14,
    )

    page.insert_text(
        (72, 110),
        "Maximum pressure: 10 bar",
        fontsize=11,
    )

    page.insert_text(
        (72, 145),
        "NOTE: Inspect valve before operation",
        fontsize=11,
    )

    pdf.save(file_path)
    pdf.close()

    return file_path