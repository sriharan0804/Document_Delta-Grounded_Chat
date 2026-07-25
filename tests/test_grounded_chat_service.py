from src.canonical.model import (
    BoundingBox,
    DocumentElement,
    ElementType,
)
from src.delta.models import (
    ChangeType,
    DeltaSummary,
    DocumentDelta,
    ElementDelta,
)
from src.grounded_chat.service import GroundedChatService


def make_element(
    element_id: str,
    content: str,
) -> DocumentElement:
    return DocumentElement(
        element_id=element_id,
        element_type=ElementType.TEXT,
        content=content,
        page_number=1,
        bbox=BoundingBox(
            x0=0.1,
            y0=0.1,
            x1=0.2,
            y1=0.2,
        ),
    )


def test_answer_contains_grounded_evidence() -> None:
    before = make_element(
        "before-pressure",
        "PRESSURE 286 BARG",
    )

    after = make_element(
        "after-pressure",
        "PRESSURE 300 BARG",
    )

    delta = DocumentDelta(
        before_pid="revision-a",
        after_pid="revision-b",
        changes=[
            ElementDelta(
                change_type=ChangeType.MODIFIED,
                before=before,
                after=after,
                text_changed=True,
                position_changed=False,
                significant=True,
            )
        ],
        summary=DeltaSummary(modified=1),
    )

    result = GroundedChatService().answer(
        question="What changed about pressure?",
        delta=delta,
    )

    assert result.grounded is True
    assert len(result.evidence) == 1
    assert "286 BARG" in result.answer
    assert "300 BARG" in result.answer


def test_answer_refuses_when_evidence_is_missing() -> None:
    delta = DocumentDelta(
        before_pid="revision-a",
        after_pid="revision-b",
        changes=[],
        summary=DeltaSummary(),
    )

    result = GroundedChatService().answer(
        question="Was the pump replaced?",
        delta=delta,
    )

    assert result.grounded is False
    assert result.evidence == []
    assert "could not find evidence" in result.answer.lower()