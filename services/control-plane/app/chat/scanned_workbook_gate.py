"""Gate scanned/image-heavy workbook runs against premature single-set completion."""

from __future__ import annotations

import re

_WORKBOOK_SIGNALS = re.compile(
    r"\b(?:workbook|assignment|worksheet|question\s+paper|learning\s+unit|unit\s+\d{4,5})\b",
    re.I,
)
_PDF_SIGNALS = re.compile(r"\.pdf\b", re.I)
_SCANNED_SIGNALS = re.compile(
    r"\b(?:pdftotext|image-only|scanned|ocr|tesseract|pdftoppm|page-\d+\.(?:png|jpg)|"
    r"near-empty|empty\s+text)\b",
    re.I,
)
_COMPLETION_CLAIM = re.compile(
    r"\bStatus:\s*COMPLETE\b|\bevery\s+question\b|\ball\s+(?:prompts|questions|activities)\b",
    re.I,
)
_LEARNING_UNIT = re.compile(r"\bLearning\s+Unit\s+\d+\b", re.I)
_SET_A_MARKERS = re.compile(
    r"\b(?:Set\s+A|Part\s+A|Question/Activity|Questions?\s+and\s+Activities?)\b",
    re.I,
)
_SET_A_LABEL = re.compile(r"\b(?:Set|Part)\s+A\b", re.I)
_SET_B_LABEL = re.compile(r"\b(?:Set|Part)\s+B\b", re.I)
_EARLY_PAGE_RANGE = re.compile(r"\bpages?\s*(?:[7-9]|1[0-8])\b", re.I)
_LATE_ONLY_PAGES = re.compile(r"\bpages?\s*(?:2[3-9]|3[0-8])\b", re.I)

_POLICY_APPENDIX = (
    "Scanned workbook policy (mandatory): when pdftotext is empty or the PDF is "
    "image-heavy, build a full-page question/activity inventory — every set, heading, "
    "and page range — before writing answers. Multi-set workbooks often include earlier "
    "Question/Activity sections (e.g. Set A) before later Learning Units (e.g. Set B). "
    "Do not print Status: COMPLETE or claim every question is answered until the "
    "inventory is checked off end-to-end."
)


def assignment_workbook_context(*texts: str) -> bool:
    combined = "\n".join(text for text in texts if text and text.strip())
    if not combined.strip():
        return False
    if not _WORKBOOK_SIGNALS.search(combined):
        return False
    return bool(_PDF_SIGNALS.search(combined) or _SCANNED_SIGNALS.search(combined))


def scanned_workbook_context(*texts: str) -> bool:
    if not assignment_workbook_context(*texts):
        return False
    combined = "\n".join(text for text in texts if text and text.strip())
    return bool(_SCANNED_SIGNALS.search(combined))


def assignment_workbook_policy_appendix(user_prompt: str, context_block: str = "") -> str:
    if scanned_workbook_context(user_prompt, context_block):
        return _POLICY_APPENDIX
    return ""


def scan_scanned_workbook_completion_risks(
    content: str,
    *,
    user_prompt: str = "",
    context_block: str = "",
) -> list[str]:
    if not scanned_workbook_context(user_prompt, context_block, content):
        return []

    text = content or ""
    if not _COMPLETION_CLAIM.search(text):
        return []

    warnings: list[str] = []

    has_inventory_heading = bool(re.search(r"\binventory\b", text, re.I))
    has_multi_set = bool(_SET_A_LABEL.search(text) and _SET_B_LABEL.search(text))
    has_broad_page_coverage = bool(
        _EARLY_PAGE_RANGE.search(text) and _LATE_ONLY_PAGES.search(text)
    )
    if not has_inventory_heading and not has_multi_set and not has_broad_page_coverage:
        warnings.append(
            "scanned workbook: completion claimed without a recorded full-page "
            "question/activity inventory"
        )

    if _LEARNING_UNIT.search(text) and not _SET_A_MARKERS.search(text):
        warnings.append(
            "scanned workbook: reply focuses on Learning Unit only — earlier "
            "Question/Activity Set A may be missing (Unit 13855 pattern)"
        )

    if _LATE_ONLY_PAGES.search(text) and not _EARLY_PAGE_RANGE.search(text):
        warnings.append(
            "scanned workbook: completion cites later pages only — earlier answer "
            "pages were not inventoried"
        )

    return warnings
