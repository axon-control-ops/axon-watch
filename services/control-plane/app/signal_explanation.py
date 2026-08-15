"""Plain-English explanation + next-step for known watch-signal failure patterns.

This is a small, deliberately narrow seed table — v1 only, per the scoping
agreed with the operator: cover the failure modes we've actually diagnosed
manually, don't attempt generic NLP translation of arbitrary signal text.

Grow this table each time a new signal pattern gets diagnosed by hand, the
same way tonight's session diagnosed the Sentry-token and CI-billing cases.
"""

from __future__ import annotations

import re
from typing import NamedTuple


class SignalExplanation(NamedTuple):
    plain_explanation: str
    next_step: str
    owner_hint: str  # "you" (needs a human/credential) or "agent" (something a worker can fix)


def _matches(summary: str, *patterns: str) -> bool:
    return any(re.search(pattern, summary, re.IGNORECASE) for pattern in patterns)


def resolve_signal_explanation(item: dict[str, object]) -> SignalExplanation | None:
    summary = str(item.get("summary") or "")
    severity = str(item.get("severity") or "")

    if severity == "critical" and _matches(
        summary,
        r"reject(ed)?\s+the\s+auth\s+token",
        r"invalid\s+(api\s*key|token)",
        r"\b401\b",
        r"\b403\b",
        r"unauthorized",
    ):
        return SignalExplanation(
            plain_explanation="A saved API key or token stopped working (expired or revoked).",
            next_step="Go to Vault, rotate the key for this connector, then click Refresh.",
            owner_hint="you",
        )

    if _matches(
        summary,
        r"billing\s+blocker",
        r"spending\s+limit",
        r"never\s+started\s+\(runner_id=0\)",
    ):
        return SignalExplanation(
            plain_explanation="GitHub Actions ran out of budget for this workflow, so the job never ran.",
            next_step="Check the GitHub Actions billing page and raise the spending limit, or wait for the next billing cycle.",
            owner_hint="you",
        )

    if _matches(summary, r"could not resolve hostname", r"could not read from remote repository"):
        return SignalExplanation(
            plain_explanation="This machine can't reach GitHub over SSH yet.",
            next_step="Restore the SSH key/config for this host (Settings → Runtime), then retry.",
            owner_hint="you",
        )

    if _matches(summary, r"no publishable changes"):
        return SignalExplanation(
            plain_explanation="The agent looked into this and found nothing left to fix in the code — the underlying issue was likely already resolved outside the codebase.",
            next_step="Safe to mark this task complete rather than retry it.",
            owner_hint="agent",
        )

    if _matches(
        summary,
        r"receipt-backed\s+ops\s+task",
        r"ops\s+task\s+required\s+no\s+publishable\s+code\s+changes",
    ):
        return SignalExplanation(
            plain_explanation="This was an operations task, so success is proven by the command receipt rather than a git diff.",
            next_step="Open the run receipt or terminal job status; if the command succeeded, the task can stay completed.",
            owner_hint="agent",
        )

    if _matches(
        summary,
        r"requires?\s+an?\s+approval",
        r"terminal[-\s]?job\s+approval",
        r"approval\s+profiles?",
    ):
        return SignalExplanation(
            plain_explanation="The worker reached a safe-control boundary and needs an attended approval before it can run the host command.",
            next_step="Approve the exact terminal job from the attended session, or pre-grant this approved wrapper in the worker runtime profile.",
            owner_hint="you",
        )

    return None
