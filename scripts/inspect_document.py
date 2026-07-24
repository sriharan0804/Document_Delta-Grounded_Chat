from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.canonical.export import (
    build_canonical_summary,
    export_canonical_json,
)
from src.ingest.pdf_native import NativePDFAdapter
from src.ingest.resolver import (
    LocalDocumentConfig,
    build_local_resolver,
)
from src.ingest.service import IngestionService


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Ingest a native PDF and export its canonical representation."
        )
    )

    parser.add_argument(
        "--pid",
        required=True,
        help="Persistent identifier for the document revision.",
    )

    parser.add_argument(
        "--file",
        required=True,
        type=Path,
        help="Path to the native PDF.",
    )

    parser.add_argument(
        "--revision",
        default=None,
        help="Optional revision label, such as A or B.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output JSON path.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    if not args.file.exists():
        raise FileNotFoundError(
            f"Input file does not exist: {args.file}"
        )

    output_path = args.output

    if output_path is None:
        safe_pid = args.pid.replace("/", "_").replace("\\", "_")
        output_path = Path("outputs") / f"{safe_pid}_canonical.json"

    resolver = build_local_resolver(
    {
        args.pid: LocalDocumentConfig(
            file_path=args.file,
            revision=args.revision,
        ),
    }
)

    source = resolver.resolve(args.pid)
    source.revision = args.revision

    service = IngestionService(
        resolver=resolver,
        adapters=[
            NativePDFAdapter(),
        ],
    )

    document = service.ingest(args.pid)

    exported_path = export_canonical_json(
        document=document,
        output_path=output_path,
    )

    summary = build_canonical_summary(document)

    print(
        json.dumps(
            summary,
            indent=2,
        )
    )

    print(f"\nCanonical JSON written to: {exported_path}")


if __name__ == "__main__":
    main()