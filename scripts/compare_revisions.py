from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.delta.service import DocumentDeltaService
from src.ingest.docling_pdf import DoclingPDFAdapter
from src.ingest.source import DocumentSource


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Ingest and compare two PDF document revisions."
        )
    )

    parser.add_argument(
        "--before",
        type=Path,
        required=True,
        help="Path to the older PDF revision.",
    )

    parser.add_argument(
        "--after",
        type=Path,
        required=True,
        help="Path to the newer PDF revision.",
    )

    parser.add_argument(
        "--before-pid",
        default="revision-a",
        help="Canonical identifier for the older revision.",
    )

    parser.add_argument(
        "--after-pid",
        default="revision-b",
        help="Canonical identifier for the newer revision.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/delta_report.json"),
        help="Path for the generated JSON delta report.",
    )

    return parser


def validate_pdf(path: Path, argument_name: str) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"{argument_name} file does not exist: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"{argument_name} path is not a file: {path}"
        )

    if path.suffix.lower() != ".pdf":
        raise ValueError(
            f"{argument_name} must be a PDF file: {path}"
        )


def main() -> None:
    args = build_parser().parse_args()

    validate_pdf(args.before, "--before")
    validate_pdf(args.after, "--after")

    adapter = DoclingPDFAdapter(
        enable_ocr=True,
        enable_tables=False,
    )

    print("\nIngesting older revision...")

    before_document = adapter.ingest(
        DocumentSource(
            pid=args.before_pid,
            file_path=args.before,
            metadata={
                "revision_role": "before",
                "source_filename": args.before.name,
            },
        )
    )

    print(
        f"Older revision: "
        f"{before_document.page_count} pages, "
        f"{before_document.element_count} elements"
    )

    print("\nIngesting newer revision...")

    after_document = adapter.ingest(
        DocumentSource(
            pid=args.after_pid,
            file_path=args.after,
            metadata={
                "revision_role": "after",
                "source_filename": args.after.name,
            },
        )
    )

    print(
        f"Newer revision: "
        f"{after_document.page_count} pages, "
        f"{after_document.element_count} elements"
    )

    print("\nAligning elements and classifying changes...")

    delta = DocumentDeltaService().compare(
        before=before_document,
        after=after_document,
    )

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.output.write_text(
        json.dumps(
            delta.model_dump(mode="json"),
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\n--- Delta summary ---")
    print(f"Before PID: {delta.before_pid}")
    print(f"After PID: {delta.after_pid}")
    print(f"Unchanged: {delta.summary.unchanged}")
    print(f"Added: {delta.summary.added}")
    print(f"Removed: {delta.summary.removed}")
    print(f"Modified: {delta.summary.modified}")
    print(f"Moved: {delta.summary.moved}")
    print(
        "Moved and modified: "
        f"{delta.summary.moved_and_modified}"
    )
    print(f"Total changes: {delta.summary.total_changes}")

    print(f"\nReport written to: {args.output}")

    changed_elements = delta.changed_elements

    if not changed_elements:
        print("\nNo changes were detected.")
        return

    print("\n--- First detected changes ---")

    for change in changed_elements[:20]:
        before_content = (
            change.before.content
            if change.before is not None
            else None
        )

        after_content = (
            change.after.content
            if change.after is not None
            else None
        )

        score = (
            change.match_score.total_score
            if change.match_score is not None
            else None
        )

        print(
            f"\nType: {change.change_type.value}"
        )
        print(f"Before: {before_content!r}")
        print(f"After:  {after_content!r}")
        print(f"Match score: {score}")


if __name__ == "__main__":
    main()