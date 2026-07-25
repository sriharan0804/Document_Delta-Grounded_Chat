from __future__ import annotations

from copy import deepcopy
from typing import Any


class AdjacentTextElementMerger:
    """Merge text fragments that likely belong to the same document note."""

    def __init__(
        self,
        *,
        max_vertical_gap: float = 12.0,
        max_horizontal_gap: float = 40.0,
        max_merged_length: int = 500,
    ) -> None:
        self.max_vertical_gap = max_vertical_gap
        self.max_horizontal_gap = max_horizontal_gap
        self.max_merged_length = max_merged_length

    def merge(self, elements: list[Any]) -> list[Any]:
        if not elements:
            return []

        ordered = sorted(
            elements,
            key=lambda element: (
                self._page_number(element),
                self._y0(element),
                self._x0(element),
            ),
        )

        merged: list[Any] = []

        for element in ordered:
            if not merged:
                merged.append(deepcopy(element))
                continue

            previous = merged[-1]

            if self._should_merge(previous, element):
                previous.content = self._join_text(
                    previous.content,
                    element.content,
                )
                self._expand_bbox(previous, element)
            else:
                merged.append(deepcopy(element))

        return merged

    def _should_merge(self, left: Any, right: Any) -> bool:
        if self._page_number(left) != self._page_number(right):
            return False

        left_text = self._text(left)
        right_text = self._text(right)

        if not left_text or not right_text:
            return False

        combined_length = len(left_text) + len(right_text) + 1
        if combined_length > self.max_merged_length:
            return False

        vertical_gap = abs(self._y0(right) - self._y1(left))
        horizontal_gap = abs(self._x0(right) - self._x1(left))

        same_line = (
            abs(self._y0(left) - self._y0(right))
            <= self.max_vertical_gap
            and horizontal_gap <= self.max_horizontal_gap
        )

        next_line = vertical_gap <= self.max_vertical_gap

        return same_line or next_line

    @staticmethod
    def _join_text(left: str, right: str) -> str:
        left = left.strip()
        right = right.strip()

        if left.endswith("-"):
            return f"{left[:-1]}{right}"

        return f"{left} {right}"

    @staticmethod
    def _expand_bbox(target: Any, source: Any) -> None:
        target.bounding_box.x0 = min(
            target.bounding_box.x0,
            source.bounding_box.x0,
        )
        target.bounding_box.y0 = min(
            target.bounding_box.y0,
            source.bounding_box.y0,
        )
        target.bounding_box.x1 = max(
            target.bounding_box.x1,
            source.bounding_box.x1,
        )
        target.bounding_box.y1 = max(
            target.bounding_box.y1,
            source.bounding_box.y1,
        )

    @staticmethod
    def _text(element: Any) -> str:
        return str(getattr(element, "content", "") or "").strip()

    @staticmethod
    def _page_number(element: Any) -> int:
        return int(getattr(element, "page_number", 0) or 0)

    @staticmethod
    def _x0(element: Any) -> float:
        return float(element.bounding_box.x0)

    @staticmethod
    def _y0(element: Any) -> float:
        return float(element.bounding_box.y0)

    @staticmethod
    def _x1(element: Any) -> float:
        return float(element.bounding_box.x1)

    @staticmethod
    def _y1(element: Any) -> float:
        return float(element.bounding_box.y1)