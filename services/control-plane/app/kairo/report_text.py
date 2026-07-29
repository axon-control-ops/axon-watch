"""Plain-language scrubbers for deterministic REPORT / theater copy."""

from __future__ import annotations

import re


_SHELL_DUMP_SPLIT = re.compile(
    r"\s+(?:terminal\b|ls\s+-la\b|find\s+/|cat\s+/|grep\s+|head\s+-|2>/dev/null)",
    re.IGNORECASE,
)
_PUSH_FAILURE_MARKER = re.compile(
    r"(?is)(?:push failed:\s*)?git push failed(?:\s*:\s*)?.*$"
)


def _push_failure_kind(text: str) -> str | None:
    hay = str(text or "").lower()
    if not any(
        marker in hay
        for marker in ("push failed", "git push failed", "push did not", "retry the push")
    ):
        return None
    if any(
        marker in hay
        for marker in (
            "protected branch",
            "branch protection",
            "protected branch hook declined",
            "changes must be made through a pull request",
        )
    ):
        return "protected_branch"
    if any(
        marker in hay
        for marker in (
            "non-fast-forward",
            "fetch first",
            "updates were rejected",
            "tip of your current branch is behind",
        )
    ):
        return "branch_behind"
    if any(
        marker in hay
        for marker in (
            "authentication failed",
            "permission denied",
            "could not read username",
            "invalid credentials",
            "repository not found",
            "http 401",
            "http 403",
        )
    ):
        return "authentication"
    if any(
        marker in hay
        for marker in (
            "could not resolve host",
            "connection timed out",
            "connection reset",
            "network is unreachable",
            "failed to connect",
        )
    ):
        return "network"
    if any(
        marker in hay
        for marker in (
            "pre-receive hook declined",
            "pre-push hook",
            "hook declined",
        )
    ):
        return "hook"
    return "unknown"


def push_failure_next_move(text: str) -> str | None:
    """Return a first-person recovery only when the push error supports it."""
    kind = _push_failure_kind(text)
    if kind == "protected_branch":
        return "I'll open the Lead receipt and use the required pull-request path"
    if kind == "branch_behind":
        return "I'll open the Lead receipt, sync the branch safely, then retry the push"
    if kind == "authentication":
        return "I'll open the Lead receipt, restore Git credentials, then retry the push"
    if kind == "network":
        return "I'll open the Lead receipt, restore connectivity, then retry the push"
    if kind == "hook":
        return "I'll open the Lead receipt, fix the rejected push hook, then retry"
    if kind == "unknown":
        return "I'll open the Lead receipt and inspect the exact push error before retrying"
    return None


def _push_failure_summary(text: str) -> str | None:
    kind = _push_failure_kind(text)
    if kind == "protected_branch":
        return "Commit landed; direct push was blocked by branch protection"
    if kind == "branch_behind":
        return "Commit landed; push was rejected because the remote branch is ahead"
    if kind == "authentication":
        return "Commit landed; push was rejected by Git authentication or permissions"
    if kind == "network":
        return "Commit landed; push could not reach the remote"
    if kind == "hook":
        return "Commit landed; a remote push hook rejected it"
    if kind == "unknown":
        return "Commit landed; push did not — inspect the Lead receipt for the exact error"
    return None


def _truncate(text: str, *, max_len: int) -> str:
    cleaned = " ".join(str(text or "").strip().split())
    if len(cleaned) <= max_len:
        return cleaned
    return f"{cleaned[: max_len - 1].rstrip()}…"


def _scrub_operator_line(text: str, *, max_len: int = 160) -> str:
    """Strip markdown / telemetry noise so theater panels and TTS stay readable."""
    cleaned = str(text or "")
    cleaned = re.sub(r"[#*`_]+", " ", cleaned)
    cleaned = re.sub(r"(?i)\binvocation\s*id[:,]?\s*[a-f0-9-]+", " ", cleaned)
    cleaned = re.sub(r"(?i)\bunit:\s*[\w.-]+", " ", cleaned)
    cleaned = re.sub(r"(?i)\bscope[,:]?\s*[\w.-]+", " ", cleaned)
    cleaned = re.sub(r"(?i)\bauth\s*=\s*missing\b", "authentication missing", cleaned)
    cleaned = re.sub(r"(?i)\bopen\s+runtime\s+or\s+/vault\b", "open Runtime or Vault", cleaned)
    # Ask-card / git dispatch laundry → short operator English.
    cleaned = re.sub(
        r"(?i)committed successfully with message:\s*selected option\s+\S+\s*:\s*",
        "Committed after your choice — ",
        cleaned,
    )
    cleaned = re.sub(
        r"(?i)committed successfully with message:\s*",
        "Committed — ",
        cleaned,
    )
    cleaned = re.sub(
        r"(?i)selected option\s+\S+\s*:\s*",
        "",
        cleaned,
    )
    push_summary = _push_failure_summary(cleaned)
    if push_summary:
        cleaned = _PUSH_FAILURE_MARKER.sub(push_summary, cleaned)
    # Collapse long CLI laundry lists into one operator phrase.
    if re.search(r"(?i)no\s+cli\s+runtime\s+is\s+ready|cli\s*\(local\)\s*unavailable", cleaned):
        cleaned = re.sub(
            r"(?i).{0,40}cannot\s+start because no CLI runtime is ready.*",
            "cannot start — no CLI runtime is ready. Open Runtime or Vault, then retry",
            cleaned,
            count=1,
        )
        cleaned = re.sub(
            r"(?i):\s*Codex CLI.*$",
            ". Open Runtime or Vault, then retry",
            cleaned,
            count=1,
        )
    if re.search(r"(?i)failed on Cursor CLI", cleaned):
        cleaned = re.sub(
            r"(?i)failed on Cursor CLI.*",
            "failed on Cursor CLI — runtime login is not ready",
            cleaned,
            count=1,
        )
    # Strip shell/path laundry from Lead handoff headlines (board must stay operator-facing).
    if _SHELL_DUMP_SPLIT.search(cleaned) or re.search(r"/home/\w+/", cleaned) or re.search(
        r"(?i)\.sqlite3?\b", cleaned
    ):
        cleaned = _SHELL_DUMP_SPLIT.split(cleaned, maxsplit=1)[0].strip(" .")
        if re.search(r"/home/\w+/", cleaned):
            cleaned = re.split(r"(?i)\s+/home/", cleaned, maxsplit=1)[0].strip(" .")
        if not cleaned:
            cleaned = "Shift completed — details are in the Lead receipts"
        elif not cleaned.endswith((".", "!", "?")):
            cleaned = f"{cleaned}."
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" :-")
    cleaned = re.sub(r"(?i)\blead next:\s*$", "", cleaned).strip(" :-")
    cleaned = re.sub(r"(?i)\blead-team\b", "Lead team", cleaned)
    cleaned = re.sub(r"\s*;\s*", ". ", cleaned)
    cleaned = re.sub(r"\.\s*\.", ".", cleaned)
    return _truncate(cleaned, max_len=max_len)


__all__ = ["_scrub_operator_line", "_truncate", "push_failure_next_move"]
