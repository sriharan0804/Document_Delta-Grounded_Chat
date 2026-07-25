from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.delta.models import DocumentDelta
from src.grounded_chat.service import GroundedChatService


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--delta",
        required=True,
        help="Path to delta JSON",
    )

    parser.add_argument(
        "--question",
        required=True,
        help="Question to ask",
    )

    args = parser.parse_args()

    data = json.loads(
        Path(args.delta).read_text(encoding="utf-8")
    )

    delta = DocumentDelta.model_validate(data)

    service = GroundedChatService()

    result = service.answer(
        question=args.question,
        delta=delta,
    )

    print("\nQuestion:")
    print(args.question)

    print("\nAnswer:")
    print(result.answer)

    print("\nEvidence:")

    if not result.evidence:
        print("None")
    else:
        for i, item in enumerate(result.evidence, start=1):
            print(f"\n[{i}] {item.change_type.value}")
            print(f"Before: {item.before_content}")
            print(f"After : {item.after_content}")


if __name__ == "__main__":
    main()