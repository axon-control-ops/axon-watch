"""Commit-subject policy derived from operator intent and changed paths."""

from __future__ import annotations

import re

INSTRUCTIONAL_TURN_RE = re.compile(
    r"^\s*(?:please\s+)?"
    r"(?:you\s+should|you\s+need\s+to|you\s+must|make\s+sure(?:\s+to)?|"
    r"be\s+sure(?:\s+to)?|ensure(?:\s+that)?|can\s+you|could\s+you|"
    r"would\s+you|i\s+want\s+you\s+to|i\s+need\s+you\s+to|"
    r"go\s+ahead(?:\s+and)?|do\s+all(?:\s+the\s+things)?|"
    r"remember\s+to|don'?t\s+forget(?:\s+to)?|try\s+to|"
    r"run\s+the|also\s+run|and\s+then\s+run)\b",
    re.IGNORECASE,
)
_COMMIT_SUBJECT_VERB_RE = re.compile(
    r"^(?:add|update|fix|fixes|fixed|remove|delete|implement|refactor|"
    r"polish|improve|wire|enable|disable|restore|revert|bump|chore|"
    r"docs|test|tests|ci|build|perf|security|hotfix|release|"
    r"slice\s+\d+)\b",
    re.IGNORECASE,
)
_TOPIC_LABELS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bcanary:ota\b|\bota:canary\b", re.IGNORECASE), "OTA canary"),
    (re.compile(r"\bota\b", re.IGNORECASE), "OTA"),
    (re.compile(r"\bcanary\b", re.IGNORECASE), "canary"),
    (re.compile(r"\bci\b", re.IGNORECASE), "CI"),
    (re.compile(r"\bsentry\b", re.IGNORECASE), "Sentry"),
)
_SCRIPT_TOPIC_RE = re.compile(
    r"(?:run(?:\s+the)?|execute|ship)\s+([a-z0-9][a-z0-9:_./-]{1,40})",
    re.IGNORECASE,
)
_INTENT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bunblock(?:ed|ing)?\b", re.IGNORECASE), "Unblock"),
    (re.compile(r"\b(?:hot)?fix(?:es|ed|ing)?\b", re.IGNORECASE), "Fix"),
    (re.compile(r"\bship(?:ping)?\b", re.IGNORECASE), "Ship"),
    (re.compile(r"\brestore(?:d|ing)?\b", re.IGNORECASE), "Restore"),
    (re.compile(r"\benable(?:d|ing)?\b", re.IGNORECASE), "Enable"),
    (re.compile(r"\bprepare|prep\b", re.IGNORECASE), "Prepare"),
    (re.compile(r"\breleas(?:e|ing)\b", re.IGNORECASE), "Release"),
)
_AREA_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("pricing", "pricing"),
    ("payment", "payments"),
    ("notif", "notifications"),
    ("push", "push channels"),
    ("workflow", "CI workflows"),
    (".github", "CI"),
    ("android", "Android"),
    ("billing", "billing"),
    ("subscription", "subscriptions"),
    ("auth", "auth"),
    ("agent", "agents"),
)


def extract_work_topic(turn_subject: str | None) -> str | None:
    """Return a short topic label even when the turn is instructional."""
    text = " ".join(str(turn_subject or "").split()).strip()
    if not text:
        return None
    for pattern, label in _TOPIC_LABELS:
        if pattern.search(text):
            return label
    script = _SCRIPT_TOPIC_RE.search(text)
    if not script:
        return None
    token = script.group(1).strip(" .:,-")
    if not token or re.fullmatch(r"commit|push|git|changes?", token, re.IGNORECASE):
        return None
    return token.replace(":", " ").replace("_", " ").replace("/", " ")[:40]


def extract_work_intent(turn_subject: str | None) -> str | None:
    """Return an action verb implied by the turn."""
    text = " ".join(str(turn_subject or "").split()).strip()
    for pattern, label in _INTENT_PATTERNS:
        if pattern.search(text):
            return label
    return None


def _collect_area_labels(files: list[str]) -> list[str]:
    areas: list[str] = []
    for path in files:
        lower = path.lower()
        matched = next((label for needle, label in _AREA_KEYWORDS if needle in lower), None)
        if matched is None:
            parts = [part for part in path.split("/") if part and not part.startswith(".")]
            if len(parts) >= 2:
                matched = (
                    parts[1]
                    if parts[0] in {"app", "apps", "components", "lib", "hooks", "features", "src"}
                    else parts[0]
                )
            elif parts:
                matched = parts[0]
            else:
                matched = path.rsplit("/", 1)[-1]
        if matched and matched not in areas:
            areas.append(matched)
        if len(areas) >= 3:
            break
    return areas


def _format_area_focus(areas: list[str], *, file_count: int) -> str:
    if not areas:
        return f"{file_count} files" if file_count else "workspace"
    if len(areas) == 1:
        focus = areas[0]
    elif len(areas) == 2:
        focus = f"{areas[0]} and {areas[1]}"
    else:
        focus = f"{areas[0]}, {areas[1]}, and {areas[2]}"
    return f"{focus} ({file_count} files)" if file_count >= 3 else focus


def summarize_change_areas(files: list[str]) -> str | None:
    """Group pending paths into product areas for a human-readable subject."""
    if len(files) < 2:
        return None
    areas = _collect_area_labels(files)
    return f"Update {_format_area_focus(areas, file_count=len(files))}" if areas else None


def compose_intent_subject(
    *,
    topic: str | None,
    intent: str | None,
    diff_subject: str | None,
    area_subject: str | None,
    files: list[str],
) -> str | None:
    """Build an intent-led subject such as ``Unblock OTA canary — pricing``."""
    if not topic and not intent:
        return None
    areas = _collect_area_labels(files)
    focus = _format_area_focus(areas, file_count=len(files)) if areas else None
    if not focus and area_subject:
        focus = re.sub(r"^(?:Add|Update|Remove)\s+", "", area_subject, flags=re.IGNORECASE)
    if not focus and diff_subject:
        focus = re.sub(r"^(?:Add|Update|Remove)\s+", "", diff_subject, flags=re.IGNORECASE)

    head = " ".join(part for part in (intent, topic) if part)
    if focus and topic and topic.lower() in focus.lower():
        subject = head
    elif focus:
        subject = f"{head} — {focus}"
    else:
        subject = head
    return f"{subject[:71].rstrip()}…" if len(subject) > 72 else subject


def compose_topic_and_diff(
    topic: str,
    diff_subject: str | None,
    area_subject: str | None,
) -> str:
    """Combine a safe topic label with a diff-derived summary."""
    body = area_subject or diff_subject or "workspace updates"
    subject = (
        body
        if topic.lower() in body.lower()
        else f"{topic}: {body[0].lower() + body[1:] if body[:1].isupper() else body}"
    )
    return f"{subject[:71].rstrip()}…" if len(subject) > 72 else subject


def looks_like_commit_subject(text: str, *, intent_only_re: re.Pattern[str]) -> bool:
    """True when text reads as a change summary, not an agent instruction."""
    cleaned = " ".join(str(text or "").split()).strip()
    if not cleaned or INSTRUCTIONAL_TURN_RE.match(cleaned) or intent_only_re.match(cleaned):
        return False
    if re.search(
        r"\b(?:make\s+sure|do\s+all\s+the\s+things|get\s+.+?\s+unblocked|"
        r"and\s+do\s+all|to\s+get\s+the)\b",
        cleaned,
        re.IGNORECASE,
    ):
        return False
    if _COMMIT_SUBJECT_VERB_RE.match(cleaned):
        return True
    if len(cleaned) <= 72 and not cleaned.endswith("?"):
        if re.search(r"[—–:\-]", cleaned) or cleaned[:1].isupper():
            return not re.search(r"\b(?:you|your|should|make sure)\b", cleaned, re.IGNORECASE)
    return False
