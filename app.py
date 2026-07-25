from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import streamlit as st

from src.chat import GroundedChatService
from src.delta.models import ChangeType, DocumentDelta, ElementDelta
from streamlit_units import compare_documents

def is_noise_change(change: ElementDelta) -> bool:
    

    before_text = get_element_content(change.before)
    after_text = get_element_content(change.after)

    text = after_text or before_text
    normalized = text.strip()

    if not normalized:
        return True

    # Ignore isolated single-character drawing labels such as P, A, 1.
    if len(normalized) == 1 and normalized.isalnum():
        return True

    return False
st.set_page_config(
    page_title="Document Delta & Grounded Chat",
    page_icon="📄",
    layout="wide",
)


def get_element_content(element: Any) -> str:
    """Safely extract readable content from a document element."""

    if element is None:
        return ""

    content = getattr(element, "content", None)

    if content is None:
        return str(element)

    return str(content).strip()


def get_element_page(element: Any) -> str:
    """Safely extract a page number from a document element."""

    if element is None:
        return "—"

    for attribute in (
        "page_number",
        "page",
        "page_index",
        "page_no",
    ):
        value = getattr(element, attribute, None)

        if value is not None:
            return str(value)

    return "—"


def change_title(change: ElementDelta, index: int) -> str:
    """Create a readable title for a detected change."""

    labels = {
        ChangeType.ADDED: "Added",
        ChangeType.REMOVED: "Removed",
        ChangeType.MODIFIED: "Modified",
        ChangeType.MOVED: "Moved",
        ChangeType.MOVED_AND_MODIFIED: "Moved and Modified",
        ChangeType.UNCHANGED: "Unchanged",
    }

    label = labels.get(
        change.change_type,
        change.change_type.value.replace("_", " ").title(),
    )

    return f"{index}. {label}"


def display_change(change: ElementDelta, index: int) -> None:
    """Display a single change without misleading None values."""

    with st.expander(change_title(change, index)):

        change_type = change.change_type

        if change_type == ChangeType.ADDED:
            st.markdown("**Added content**")
            st.write(
                get_element_content(change.after)
                or "No readable content available."
            )

            page = get_element_page(change.after)

            if page != "—":
                st.caption(f"Revised page: {page}")

        elif change_type == ChangeType.REMOVED:
            st.markdown("**Removed content**")
            st.write(
                get_element_content(change.before)
                or "No readable content available."
            )

            page = get_element_page(change.before)

            if page != "—":
                st.caption(f"Original page: {page}")

        else:
            before_column, after_column = st.columns(2)

            with before_column:
                st.markdown("**Original**")
                st.write(
                    get_element_content(change.before)
                    or "No readable original content."
                )
                page = get_element_page(change.before)

                if page != "—":
                    st.caption(f"Page: {page}")

            with after_column:
                st.markdown("**Revised**")
                st.write(
                    get_element_content(change.after)
                    or "No readable revised content."
                )
                page = get_element_page(change.after)

                if page != "—":
                    st.caption(f"Page: {page}")

        if change.match_score is not None:
            st.markdown("**Comparison score**")

            score_columns = st.columns(4)

            score_columns[0].metric(
                "Overall",
                f"{change.match_score.total_score:.2f}",
            )
            score_columns[1].metric(
                "Text",
                f"{change.match_score.text_similarity:.2f}",
            )
            score_columns[2].metric(
                "Spatial",
                f"{change.match_score.spatial_similarity:.2f}",
            )
            score_columns[3].metric(
                "Type",
                f"{change.match_score.type_similarity:.2f}",
            )

        details = []

        if change.text_changed:
            details.append("Text changed")

        if change.position_changed:
            details.append("Position changed")

        if change.significance_reason:
            details.append(change.significance_reason)

        if details:
            st.caption(" · ".join(details))


def build_markdown_report(delta: DocumentDelta) -> str:
    """Generate a downloadable Markdown delta report."""

    summary = delta.summary

    lines = [
        "# Document Delta Report",
        "",
        f"- Original revision: `{delta.before_pid}`",
        f"- Revised revision: `{delta.after_pid}`",
        f"- Total changes: **{summary.total_changes}**",
        "",
        "## Summary",
        "",
        f"- Added: {summary.added}",
        f"- Removed: {summary.removed}",
        f"- Modified: {summary.modified}",
        f"- Moved: {summary.moved}",
        (
            "- Moved and modified: "
            f"{summary.moved_and_modified}"
        ),
        "",
        "## Detected Changes",
        "",
    ]

    for index, change in enumerate(
        delta.changed_elements,
        start=1,
    ):
        label = (
            change.change_type.value
            .replace("_", " ")
            .title()
        )

        lines.extend(
            [
                f"### {index}. {label}",
                "",
            ]
        )

        if change.change_type == ChangeType.ADDED:
            lines.extend(
                [
                    "**Added:**",
                    "",
                    get_element_content(change.after)
                    or "No readable content.",
                    "",
                ]
            )

        elif change.change_type == ChangeType.REMOVED:
            lines.extend(
                [
                    "**Removed:**",
                    "",
                    get_element_content(change.before)
                    or "No readable content.",
                    "",
                ]
            )

        else:
            lines.extend(
                [
                    "**Before:**",
                    "",
                    get_element_content(change.before)
                    or "No readable content.",
                    "",
                    "**After:**",
                    "",
                    get_element_content(change.after)
                    or "No readable content.",
                    "",
                ]
            )

        if change.match_score is not None:
            lines.extend(
                [
                    (
                        "**Overall match score:** "
                        f"{change.match_score.total_score:.3f}"
                    ),
                    "",
                ]
            )

    return "\n".join(lines)
def build_grounded_chat_report(delta: DocumentDelta) -> dict:
    normalized_changes = []

    for index, change in enumerate(
        delta.changed_elements,
        start=1,
    ):
        before_text = get_element_content(change.before)
        after_text = get_element_content(change.after)

        if change.change_type == ChangeType.ADDED:
            evidence_text = f"Added element: {after_text}"

        elif change.change_type == ChangeType.REMOVED:
            evidence_text = f"Removed element: {before_text}"

        elif change.change_type == ChangeType.MODIFIED:
            evidence_text = (
                f"Modified element. "
                f"Before: {before_text}. "
                f"After: {after_text}."
            )

        elif change.change_type == ChangeType.MOVED:
            evidence_text = (
                f"Moved element: {after_text or before_text}"
            )

        elif change.change_type == ChangeType.MOVED_AND_MODIFIED:
            evidence_text = (
                f"Moved and modified element. "
                f"Before: {before_text}. "
                f"After: {after_text}."
            )

        else:
            evidence_text = (
                f"Before: {before_text}. "
                f"After: {after_text}."
            )

        normalized_changes.append(
            {
                "change_id": f"change-{index}",
                "change_type": change.change_type.value,
                "before_text": before_text,
                "after_text": after_text,
                "content": evidence_text,
                "text": evidence_text,
                "evidence_text": evidence_text,
                "significant": change.significant,
                "significance_reason": (
                    change.significance_reason
                ),
            }
        )

    return {
        "before_pid": delta.before_pid,
        "after_pid": delta.after_pid,
        "summary": delta.summary.model_dump(mode="json"),
        "changes": normalized_changes,
        "changed_elements": normalized_changes,
        "report_text": "\n".join(
            item["evidence_text"]
            for item in normalized_changes
        ),
    }

st.title("📄 Document Delta & Grounded Chat")
def answer_question_from_delta(
    question: str,
    delta: DocumentDelta,
) -> dict:
    """Answer common questions directly from the detected delta."""

    normalized_question = question.lower().strip()

    visible_changes = [
        change
        for change in delta.changed_elements
        if not is_noise_change(change)
    ]

    added = [
        get_element_content(change.after)
        for change in visible_changes
        if change.change_type == ChangeType.ADDED
        and get_element_content(change.after)
    ]

    removed = [
        get_element_content(change.before)
        for change in visible_changes
        if change.change_type == ChangeType.REMOVED
        and get_element_content(change.before)
    ]

    modified = [
        {
            "before": get_element_content(change.before),
            "after": get_element_content(change.after),
        }
        for change in visible_changes
        if change.change_type == ChangeType.MODIFIED
    ]

    moved = [
        get_element_content(change.after)
        or get_element_content(change.before)
        for change in visible_changes
        if change.change_type == ChangeType.MOVED
    ]

    moved_and_modified = [
        {
            "before": get_element_content(change.before),
            "after": get_element_content(change.after),
        }
        for change in visible_changes
        if change.change_type
        == ChangeType.MOVED_AND_MODIFIED
    ]

    evidence = []

    # Exact-content search
    matching_elements = []

    for change in visible_changes:
        before_text = get_element_content(change.before)
        after_text = get_element_content(change.after)

        combined_text = f"{before_text} {after_text}".lower()

        meaningful_words = [
            word.strip(".,?!'\"()[]{}")
            for word in normalized_question.split()
            if len(word.strip(".,?!'\"()[]{}")) >= 3
        ]

        if meaningful_words and any(
            word in combined_text
            for word in meaningful_words
        ):
            matching_elements.append(change)

    # Added questions
    if "added" in normalized_question or "new" in normalized_question:
        if not added:
            answer = "No added elements were detected."

        else:
            answer = (
                f"{len(added)} added element(s) were detected:\n\n"
                + "\n".join(
                    f"- {content}"
                    for content in added
                )
            )

            evidence = [
                {
                    "change_type": "added",
                    "content": content,
                }
                for content in added
            ]

        return {
            "answer": answer,
            "grounded": True,
            "citations": evidence,
        }

    # Removed questions
    if (
        "removed" in normalized_question
        or "deleted" in normalized_question
    ):
        if not removed:
            answer = "No removed elements were detected."

        else:
            answer = (
                f"{len(removed)} removed element(s) were detected:\n\n"
                + "\n".join(
                    f"- {content}"
                    for content in removed
                )
            )

            evidence = [
                {
                    "change_type": "removed",
                    "content": content,
                }
                for content in removed
            ]

        return {
            "answer": answer,
            "grounded": True,
            "citations": evidence,
        }

    # Modified questions
    if (
        "modified" in normalized_question
        or "changed" in normalized_question
        or "text change" in normalized_question
    ):
        if not modified and not moved_and_modified:
            answer = "No modified elements were detected."

        else:
            lines = []

            for item in modified:
                lines.append(
                    f"- Before: {item['before']}\n"
                    f"  After: {item['after']}"
                )

            for item in moved_and_modified:
                lines.append(
                    f"- Before: {item['before']}\n"
                    f"  After: {item['after']} "
                    "(also moved)"
                )

            answer = (
                "The following modified elements were detected:\n\n"
                + "\n".join(lines)
            )

            evidence = [
                {
                    "change_type": "modified",
                    **item,
                }
                for item in modified
            ]

            evidence.extend(
                {
                    "change_type": "moved_and_modified",
                    **item,
                }
                for item in moved_and_modified
            )

        return {
            "answer": answer,
            "grounded": True,
            "citations": evidence,
        }

    # Moved questions
    if "moved" in normalized_question:
        if not moved and not moved_and_modified:
            answer = "No moved elements were detected."

        else:
            moved_texts = moved + [
                item["after"] or item["before"]
                for item in moved_and_modified
            ]

            answer = (
                f"{len(moved_texts)} moved element(s) were detected:\n\n"
                + "\n".join(
                    f"- {content}"
                    for content in moved_texts
                    if content
                )
            )

            evidence = [
                {
                    "change_type": "moved",
                    "content": content,
                }
                for content in moved_texts
                if content
            ]

        return {
            "answer": answer,
            "grounded": True,
            "citations": evidence,
        }

    # Count questions
    if (
        "how many" in normalized_question
        or "number of changes" in normalized_question
    ):
        answer = (
            f"The report contains {len(visible_changes)} meaningful "
            f"change(s): {len(added)} added, {len(removed)} removed, "
            f"{len(modified)} modified, {len(moved)} moved, and "
            f"{len(moved_and_modified)} moved and modified."
        )

        return {
            "answer": answer,
            "grounded": True,
            "citations": [
                {
                    "total": len(visible_changes),
                    "added": len(added),
                    "removed": len(removed),
                    "modified": len(modified),
                    "moved": len(moved),
                    "moved_and_modified": len(
                        moved_and_modified
                    ),
                }
            ],
        }

    # Questions containing a specific detected element
    if matching_elements:
        matching_evidence = []
        answer_lines = []

        for change in matching_elements:
            before_text = get_element_content(change.before)
            after_text = get_element_content(change.after)

            if change.change_type == ChangeType.ADDED:
                answer_lines.append(
                    f"- `{after_text}` was added."
                )

            elif change.change_type == ChangeType.REMOVED:
                answer_lines.append(
                    f"- `{before_text}` was removed."
                )

            elif change.change_type == ChangeType.MODIFIED:
                answer_lines.append(
                    f"- `{before_text}` was modified to "
                    f"`{after_text}`."
                )

            elif change.change_type == ChangeType.MOVED:
                answer_lines.append(
                    f"- `{after_text or before_text}` was moved."
                )

            else:
                answer_lines.append(
                    f"- `{before_text}` changed to "
                    f"`{after_text}` and was moved."
                )

            matching_evidence.append(
                {
                    "change_type": change.change_type.value,
                    "before": before_text,
                    "after": after_text,
                }
            )

        return {
            "answer": "\n".join(answer_lines),
            "grounded": True,
            "citations": matching_evidence,
        }

    # General summary
    if (
        "summary" in normalized_question
        or "summarize" in normalized_question
        or "what changes" in normalized_question
        or "difference" in normalized_question
        or "compare" in normalized_question
    ):
        lines = [
            f"The comparison detected {len(visible_changes)} "
            "meaningful change(s).",
            f"- Added: {len(added)}",
            f"- Removed: {len(removed)}",
            f"- Modified: {len(modified)}",
            f"- Moved: {len(moved)}",
            (
                "- Moved and modified: "
                f"{len(moved_and_modified)}"
            ),
        ]

        if added:
            lines.append(
                "\nExamples of added elements:\n"
                + "\n".join(
                    f"- {content}"
                    for content in added[:5]
                )
            )

        if removed:
            lines.append(
                "\nExamples of removed elements:\n"
                + "\n".join(
                    f"- {content}"
                    for content in removed[:5]
                )
            )

        return {
            "answer": "\n".join(lines),
            "grounded": True,
            "citations": [
                {
                    "change_type": change.change_type.value,
                    "before": get_element_content(change.before),
                    "after": get_element_content(change.after),
                }
                for change in visible_changes[:10]
            ],
        }

    return {
        "answer": (
            "I could not match that question to the detected changes. "
            "Try asking: “What elements were added?”, "
            "“What was removed?”, or “Summarize the changes.”"
        ),
        "grounded": False,
        "citations": [],
    }
st.caption(
    "Compare engineering-document revisions, inspect detected changes, "
    "and ask grounded questions over the resulting delta report."
)

compare_tab, report_tab, chat_tab = st.tabs(
    [
        "Compare Documents",
        "Delta Report",
        "Grounded Chat",
    ]
)

# ============================================================
# Compare documents
# ============================================================

with compare_tab:
    st.header("Upload Document Revisions")

    original_column, revised_column = st.columns(2)

    with original_column:
        original = st.file_uploader(
            "Original PDF",
            type=["pdf"],
            key="original_pdf",
        )

    with revised_column:
        revised = st.file_uploader(
            "Revised PDF",
            type=["pdf"],
            key="revised_pdf",
        )

    compare_clicked = st.button(
        "Compare Documents",
        type="primary",
        use_container_width=True,
    )

    if compare_clicked:
        if original is None or revised is None:
            st.error(
                "Upload both the original and revised PDF files."
            )

        else:
            before_path: Path | None = None
            after_path: Path | None = None

            try:
                with tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=".pdf",
                ) as before_file:
                    before_file.write(original.getvalue())
                    before_path = Path(before_file.name)

                with tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=".pdf",
                ) as after_file:
                    after_file.write(revised.getvalue())
                    after_path = Path(after_file.name)

                with st.spinner(
                    "Ingesting PDFs and detecting changes..."
                ):
                    delta = compare_documents(
                        before_pdf=before_path,
                        after_pdf=after_path,
                    )

                st.session_state["delta"] = delta

                st.success(
                    "Comparison completed. Open the Delta Report tab."
                )

                st.metric(
                    "Total detected changes",
                    delta.summary.total_changes,
                )

            except Exception as error:
                st.error("Document comparison failed.")
                st.exception(error)

            finally:
                for temporary_path in (
                    before_path,
                    after_path,
                ):
                    if temporary_path is not None:
                        try:
                            temporary_path.unlink(
                                missing_ok=True
                            )
                        except OSError:
                            pass

# ============================================================
# Delta report
# ============================================================

with report_tab:
    if "delta" not in st.session_state:
        st.info(
            "Upload and compare two PDFs to generate a delta report."
        )

    else:
        delta: DocumentDelta = st.session_state["delta"]

        visible_changes = [
            change
            for change in delta.changed_elements
            if not is_noise_change(change)
        ]

        summary_counts = {
            ChangeType.ADDED: 0,
            ChangeType.REMOVED: 0,
            ChangeType.MODIFIED: 0,
            ChangeType.MOVED: 0,
            ChangeType.MOVED_AND_MODIFIED: 0,
        }

        for change in visible_changes:
            if change.change_type in summary_counts:
                summary_counts[change.change_type] += 1

        st.header("Delta Summary")

        summary_columns = st.columns(6)

        summary_columns[0].metric(
            "Total Changes",
            len(visible_changes),
        )

        summary_columns[1].metric(
            "Added",
            summary_counts[ChangeType.ADDED],
        )

        summary_columns[2].metric(
            "Removed",
            summary_counts[ChangeType.REMOVED],
        )

        summary_columns[3].metric(
            "Modified",
            summary_counts[ChangeType.MODIFIED],
        )

        summary_columns[4].metric(
            "Moved",
            summary_counts[ChangeType.MOVED],
        )

        summary_columns[5].metric(
            "Moved + Modified",
            summary_counts[ChangeType.MOVED_AND_MODIFIED],
        )

        st.divider()

        filter_options = [
            "All",
            "Added",
            "Removed",
            "Modified",
            "Moved",
            "Moved and Modified",
        ]

        selected_filter = st.selectbox(
            "Filter changes",
            filter_options,
            key="change_filter",
        )

        filter_mapping = {
            "Added": ChangeType.ADDED,
            "Removed": ChangeType.REMOVED,
            "Modified": ChangeType.MODIFIED,
            "Moved": ChangeType.MOVED,
            "Moved and Modified": ChangeType.MOVED_AND_MODIFIED,
        }

        changes = visible_changes

        if selected_filter != "All":
            expected_type = filter_mapping[selected_filter]

            changes = [
                change
                for change in changes
                if change.change_type == expected_type
            ]

        st.subheader(
            f"Detected Changes ({len(changes)})"
        )

        if not changes:
            st.info(
                "No changes match the selected filter."
            )

        else:
            for index, change in enumerate(
                changes,
                start=1,
            ):
                display_change(change, index)

        st.divider()

        report_dictionary = delta.model_dump(mode="json")

        json_report = json.dumps(
            report_dictionary,
            indent=2,
        )

        markdown_report = build_markdown_report(delta)

        download_column_1, download_column_2 = st.columns(2)

        with download_column_1:
            st.download_button(
                "Download JSON Report",
                data=json_report,
                file_name="delta_report.json",
                mime="application/json",
                use_container_width=True,
            )

        with download_column_2:
            st.download_button(
                "Download Markdown Report",
                data=markdown_report,
                file_name="delta_report.md",
                mime="text/markdown",
                use_container_width=True,
            )

# ============================================================
# Grounded chat
# ============================================================

with chat_tab:
    st.header("Grounded Chat")

    if "delta" not in st.session_state:
        st.info(
            "Run a document comparison before asking questions."
        )

    else:
        st.caption(
            "Answers are generated only from evidence in the delta report."
        )

        question = st.text_input(
            "Ask about the detected changes",
            placeholder=(
                "Example: Which elements were added or modified?"
            ),
        )

        max_evidence = st.slider(
            "Maximum evidence items",
            min_value=1,
            max_value=10,
            value=5,
        )

        if st.button(
            "Ask Question",
            type="primary",
            use_container_width=True,
        ):
            if not question.strip():
                st.warning("Enter a question first.")

            else:
                try:
                    delta: DocumentDelta = st.session_state["delta"]

                    with st.spinner(
                        "Searching the detected changes..."
                    ):
                        result = answer_question_from_delta(
                            question=question,
                            delta=delta,
                        )

                    st.subheader("Answer")
                    st.write(result.get("answer", ""))

                    grounded = result.get(
                        "grounded",
                        False,
                    )

                    if grounded:
                        st.success(
                            "Answer generated from the detected delta report."
                        )
                    else:
                        st.warning(
                            "No matching evidence was found."
                        )

                    citations = result.get(
                        "citations",
                        [],
                    )

                    if citations:
                        st.subheader("Supporting Evidence")

                        for index, citation in enumerate(
                            citations,
                            start=1,
                        ):
                            with st.expander(
                                f"Evidence {index}"
                            ):
                                if isinstance(citation, dict):
                                    st.json(citation)
                                else:
                                    st.write(citation)

                except Exception as error:
                    st.error(
                        "Grounded chat could not answer the question."
                    )
                    st.exception(error)