from __future__ import annotations

import argparse
from pathlib import Path

from docling.document_converter import DocumentConverter


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect Docling document items and provenance."
    )

    parser.add_argument(
        "--file",
        required=True,
        type=Path,
        help="Path to a PDF file.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of items to print.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    if not args.file.exists():
        raise FileNotFoundError(
            f"PDF does not exist: {args.file}"
        )

    converter = DocumentConverter()
    result = converter.convert(args.file)

    document = result.document

    print(f"Document pages: {len(document.pages)}")
    print("\n--- Document items ---\n")

    printed_items = 0

    for item, level in document.iterate_items():
        text = getattr(item, "text", None)
        label = getattr(item, "label", None)
        provenance = getattr(item, "prov", [])

        if not text:
            continue

        print("=" * 80)
        print(f"Item type: {type(item).__name__}")
        print(f"Hierarchy level: {level}")
        print(f"Label: {label}")
        print(f"Text: {text!r}")

        if provenance:
            for index, prov in enumerate(provenance):
                print(f"Provenance #{index}")
                print(f"  Page number: {prov.page_no}")
                print(f"  Bounding box: {prov.bbox}")
                print(
                    "  Coordinate origin: "
                    f"{prov.bbox.coord_origin}"
                )
                print(f"  Character span: {prov.charspan}")
        else:
            print("Provenance: none")

        printed_items += 1

        if printed_items >= args.limit:
            break

    print(f"\nPrinted items: {printed_items}")


if __name__ == "__main__":
    main()