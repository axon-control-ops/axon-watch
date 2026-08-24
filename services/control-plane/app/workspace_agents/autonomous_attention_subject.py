"""Structured affected-role metadata for autonomy decisions."""

from __future__ import annotations

import re

from app.workspace_agents.lead_checkin_assign import LeadCheckinFinding


_FAILED_SHIFT_RUN_RE = re.compile(r"\[run=([^\]]+)\]", re.IGNORECASE)


def decision_subject_payload(finding: LeadCheckinFinding) -> dict[str, str]:
    prefix = f"failed_shift:{finding.workspace_id}:"
    if not finding.dedupe_key.startswith(prefix):
        return {}
    subject_role = finding.dedupe_key[len(prefix) :].split(":", 1)[0].strip().lower()
    run_match = _FAILED_SHIFT_RUN_RE.search(finding.detail or "")
    payload = {"subject_role": subject_role} if subject_role else {}
    if run_match and run_match.group(1).strip():
        payload["subject_run_id"] = run_match.group(1).strip()
    return payload


__all__ = ["decision_subject_payload"]
