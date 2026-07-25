from __future__ import annotations

import json
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile

from src.api.schemas import (
    DeltaCompareResponse,
    DeltaSummary,
    HealthResponse,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPLOAD_DIRECTORY = PROJECT_ROOT / "outputs" / "uploads"
REPORT_DIRECTORY = PROJECT_ROOT / "outputs" / "api_reports"

UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
REPORT_DIRECTORY.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Document Delta & Grounded Chat API",
    description=(
        "Compare engineering-document revisions and ask grounded questions "
        "over the documents and generated delta report."
    ),
    version="1.0.0",
)


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
)
def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service="document-delta-grounded-chat",
    )


@app.post(
    "/delta/compare",
    response_model=DeltaCompareResponse,
    tags=["Delta"],
)
async def compare_documents(
    before_file: UploadFile = File(...),
    after_file: UploadFile = File(...),
) -> DeltaCompareResponse:
    _validate_pdf(before_file)
    _validate_pdf(after_file)

    report_id = uuid.uuid4().hex

    before_path = UPLOAD_DIRECTORY / f"{report_id}_before.pdf"
    after_path = UPLOAD_DIRECTORY / f"{report_id}_after.pdf"
    report_path = REPORT_DIRECTORY / f"{report_id}.json"

    try:
        await _save_upload(before_file, before_path)
        await _save_upload(after_file, after_path)

        command = [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "compare_revisions.py"),
            "--before",
            str(before_path),
            "--after",
            str(after_path),
            "--output",
            str(report_path),
        ]

        process = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )

        if process.returncode != 0:
            error_message = process.stderr.strip() or process.stdout.strip()

            raise HTTPException(
                status_code=500,
                detail=(
                    "Document comparison failed. "
                    f"{error_message or 'No error details were returned.'}"
                ),
            )

        if not report_path.exists():
            raise HTTPException(
                status_code=500,
                detail="The comparison completed but no delta report was created.",
            )

        report_data = _read_json(report_path)
        changes = _extract_changes(report_data)
        summary = _build_summary(report_data, changes)

        return DeltaCompareResponse(
            success=True,
            report_id=report_id,
            report_path=str(report_path.relative_to(PROJECT_ROOT)),
            summary=summary,
            changes=changes,
        )

    finally:
        await before_file.close()
        await after_file.close()


@app.get(
    "/delta/{report_id}",
    response_model=DeltaCompareResponse,
    tags=["Delta"],
)
def get_delta_report(report_id: str) -> DeltaCompareResponse:
    safe_report_id = _validate_report_id(report_id)
    report_path = REPORT_DIRECTORY / f"{safe_report_id}.json"

    if not report_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Delta report not found.",
        )

    report_data = _read_json(report_path)
    changes = _extract_changes(report_data)
    summary = _build_summary(report_data, changes)

    return DeltaCompareResponse(
        success=True,
        report_id=safe_report_id,
        report_path=str(report_path.relative_to(PROJECT_ROOT)),
        summary=summary,
        changes=changes,
    )


def _validate_pdf(upload: UploadFile) -> None:
    filename = upload.filename or ""

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail=f"Only PDF files are currently supported: {filename}",
        )


async def _save_upload(
    upload: UploadFile,
    destination: Path,
) -> None:
    content = await upload.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail=f"Uploaded file is empty: {upload.filename}",
        )

    destination.write_bytes(content)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=500,
            detail=f"Generated delta report is not valid JSON: {error}",
        ) from error


def _extract_changes(
    report_data: dict[str, Any],
) -> list[dict[str, Any]]:
    changes = report_data.get("changes", [])

    if not isinstance(changes, list):
        return []

    return [
        change
        for change in changes
        if (
            isinstance(change, dict)
            and change.get("significant", True)
            and str(change.get("change_type", "")).lower()
            != "unchanged"
        )
    ]


def _build_summary(
    report_data: dict[str, Any],
    changes: list[dict[str, Any]],
) -> DeltaSummary:
    counts = {
        "added": 0,
        "removed": 0,
        "modified": 0,
        "moved": 0,
        "moved_and_modified": 0,
        "unchanged": 0,
    }

    for change in changes:
        raw_change_type = str(
            change.get("change_type", "")
        ).strip().lower()

        normalized_change_type = raw_change_type.replace(
            " ",
            "_",
        )

        if normalized_change_type in counts:
            counts[normalized_change_type] += 1

    return DeltaSummary(
        total_changes=(
            counts["added"]
            + counts["removed"]
            + counts["modified"]
            + counts["moved"]
            + counts["moved_and_modified"]
        ),
        **counts,
    )


def _validate_report_id(report_id: str) -> str:
    try:
        return uuid.UUID(hex=report_id).hex
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="Invalid report ID.",
        ) from error