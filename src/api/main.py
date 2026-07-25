from __future__ import annotations

import json
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile

from src.api.schemas import (
    ChatAskRequest,
    ChatAskResponse,
    DeltaCompareResponse,
    DeltaSummary,
    HealthResponse,
)
from src.chat import GroundedChatService


PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPLOAD_DIRECTORY = PROJECT_ROOT / "outputs" / "uploads"
REPORT_DIRECTORY = PROJECT_ROOT / "outputs" / "api_reports"

UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
REPORT_DIRECTORY.mkdir(parents=True, exist_ok=True)


app = FastAPI(
    title="Document Delta & Grounded Chat API",
    description=(
        "Compare engineering-document revisions and ask grounded questions "
        "over generated delta reports."
    ),
    version="1.0.0",
)


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
)
def health_check() -> HealthResponse:
    """Return the current API health status."""

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
    """
    Compare two PDF revisions and generate a delta report.

    The original and revised PDFs are stored temporarily, passed to the
    comparison script, and converted into a structured JSON response.
    """

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
            error_message = (
                process.stderr.strip()
                or process.stdout.strip()
                or "No error details were returned."
            )

            raise HTTPException(
                status_code=500,
                detail=f"Document comparison failed. {error_message}",
            )

        if not report_path.is_file():
            raise HTTPException(
                status_code=500,
                detail=(
                    "The comparison completed, but no delta report "
                    "was created."
                ),
            )

        report_data = _read_json(report_path)
        changes = _extract_changes(report_data)
        summary = _build_summary(changes)

        return DeltaCompareResponse(
            success=True,
            report_id=report_id,
            report_path=str(report_path.relative_to(PROJECT_ROOT)),
            summary=summary,
            changes=changes,
        )

    except subprocess.TimeoutExpired as error:
        raise HTTPException(
            status_code=504,
            detail="Document comparison exceeded the 300-second timeout.",
        ) from error

    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail=f"Document comparison could not be started: {error}",
        ) from error

    finally:
        await before_file.close()
        await after_file.close()


@app.get(
    "/delta/{report_id}",
    response_model=DeltaCompareResponse,
    tags=["Delta"],
)
def get_delta_report(report_id: str) -> DeltaCompareResponse:
    """Retrieve an existing delta report by its identifier."""

    safe_report_id = _validate_report_id(report_id)
    report_path = _get_report_path(safe_report_id)

    report_data = _read_json(report_path)
    changes = _extract_changes(report_data)
    summary = _build_summary(changes)

    return DeltaCompareResponse(
        success=True,
        report_id=safe_report_id,
        report_path=str(report_path.relative_to(PROJECT_ROOT)),
        summary=summary,
        changes=changes,
    )


@app.post(
    "/chat/ask",
    response_model=ChatAskResponse,
    tags=["Grounded Chat"],
)
def ask_grounded_question(
    request: ChatAskRequest,
) -> ChatAskResponse:
    

    safe_report_id = _validate_report_id(request.report_id)
    report_path = _get_report_path(safe_report_id)
    report_data = _read_json(report_path)

    service = GroundedChatService(
        max_evidence=request.max_evidence,
    )

    try:
        result = service.answer(
            question=request.question,
            report=report_data,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    return ChatAskResponse(
        success=True,
        report_id=safe_report_id,
        question=request.question,
        answer=result["answer"],
        grounded=result["grounded"],
        evidence_count=result["evidence_count"],
        citations=result["citations"],
    )


def _validate_pdf(upload: UploadFile) -> None:
    """Validate that an uploaded document is a PDF."""

    filename = upload.filename or ""

    if not filename:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file must have a filename.",
        )

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail=f"Only PDF files are currently supported: {filename}",
        )


async def _save_upload(
    upload: UploadFile,
    destination: Path,
) -> None:
    """Save an uploaded file to the local upload directory."""

    try:
        content = await upload.read()
    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail=f"Could not read uploaded file: {upload.filename}",
        ) from error

    if not content:
        raise HTTPException(
            status_code=400,
            detail=f"Uploaded file is empty: {upload.filename}",
        )

    try:
        destination.write_bytes(content)
    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail=f"Could not save uploaded file: {upload.filename}",
        ) from error


def _get_report_path(report_id: str) -> Path:
    """Resolve and validate the path of an existing delta report."""

    report_path = REPORT_DIRECTORY / f"{report_id}.json"

    if not report_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Delta report not found.",
        )

    return report_path


def _read_json(path: Path) -> dict[str, Any]:
    """Read and validate a JSON object from disk."""

    try:
        report_data = json.loads(
            path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=500,
            detail=f"Generated delta report is not valid JSON: {error}",
        ) from error
    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail=f"Delta report could not be read: {error}",
        ) from error

    if not isinstance(report_data, dict):
        raise HTTPException(
            status_code=500,
            detail="Delta report must contain a JSON object.",
        )

    return report_data


def _extract_changes(
    report_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Return significant reportable changes.

    Unchanged and insignificant elements are excluded from the API response
    and grounded-chat evidence.
    """

    changes = report_data.get("changes", [])

    if not isinstance(changes, list):
        raise HTTPException(
            status_code=500,
            detail="Delta report has an invalid 'changes' field.",
        )

    return [
        change
        for change in changes
        if (
            isinstance(change, dict)
            and change.get("significant", True)
            and _normalize_change_type(
                change.get("change_type")
            ) != "unchanged"
        )
    ]


def _build_summary(
    changes: list[dict[str, Any]],
) -> DeltaSummary:
    """Build summary counts from the filtered report changes."""

    counts = {
        "added": 0,
        "removed": 0,
        "modified": 0,
        "moved": 0,
        "moved_and_modified": 0,
        "unchanged": 0,
    }

    for change in changes:
        change_type = _normalize_change_type(
            change.get("change_type")
        )

        if change_type in counts:
            counts[change_type] += 1

    total_changes = sum(
        counts[change_type]
        for change_type in (
            "added",
            "removed",
            "modified",
            "moved",
            "moved_and_modified",
        )
    )

    return DeltaSummary(
        total_changes=total_changes,
        **counts,
    )


def _normalize_change_type(value: Any) -> str:
    """Convert change-type values into a consistent snake_case form."""

    return (
        str(value or "")
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )


def _validate_report_id(report_id: str) -> str:
    """Validate and normalize a UUID-based report identifier."""

    try:
        return uuid.UUID(hex=report_id).hex
    except (ValueError, AttributeError) as error:
        raise HTTPException(
            status_code=400,
            detail="Invalid report ID.",
        ) from error