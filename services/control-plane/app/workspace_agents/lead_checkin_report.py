"""Operator-readable Lead team-health check-in body."""

from __future__ import annotations

import re

from app.workspace_agents.lead_checkin_assign import CHECKIN_GOAL_PREFIX, LeadCheckinFinding

_GATE6_RE = re.compile(r"gate 6|acceptance_evidence|acceptance evidence", re.IGNORECASE)
_SCOPE_RE = re.compile(r"out_of_scope|out of scope", re.IGNORECASE)
_LANE_B_RE = re.compile(r"^Lane B finalization failed:\s*", re.IGNORECASE)
_RUN_TAIL_RE = re.compile(r"\s*\[[^\]]*run[^\]]*\]\s*$", re.IGNORECASE)


def humanize_lead_failure_detail(detail: str) -> str:
    raw = " ".join(str(detail or "").split()).strip()
    if not raw:
        return "No extra detail."
    lowered = raw.lower()
    if "out of usage" in lowered or "increase limits" in lowered:
        return "Cursor usage is exhausted. Raise the limit, then retry this shift."
    if "unpaid invoice" in lowered or "credit balance" in lowered or "billing" in lowered:
        return "Billing is blocking this shift. Clear the invoice, then retry."
    if any(token in lowered for token in ("not signed in", "authentication", "api_key_invalid", "auth probe")):
        return "The agent runtime is not signed in. Unlock auth, then retry."
    if _GATE6_RE.search(raw) and _SCOPE_RE.search(raw):
        return (
            "Delivery was blocked: acceptance did not pass (Gate 6) "
            "because the change was marked out of scope."
        )
    if _GATE6_RE.search(raw):
        return "Delivery was blocked: acceptance evidence did not pass (Gate 6)."
    if _LANE_B_RE.match(raw):
        inner = _LANE_B_RE.sub("", raw).strip()
        return humanize_lead_failure_detail(inner) if inner else "The shift could not finish delivery."
    cleaned = _RUN_TAIL_RE.sub("", raw).strip()
    return re.sub(r"\s*\|\s*acceptance=fail.*$", "", cleaned).strip() or cleaned


def _next_steps(findings: list[LeadCheckinFinding]) -> list[str]:
    if not findings:
        return ["No failed shifts or degraded signals this pass. Keep the team on the current work."]
    steps: list[str] = []
    for finding in findings[:4]:
        if finding.escalate_only:
            steps.append(
                f"Unblock {finding.title} — this needs an operator gate, not another auto-retry."
            )
            continue
        if finding.kind == "failed_shift":
            steps.append(
                f"Inspect {finding.title}, then retry only if the acceptance/scope issue is fixed."
            )
            continue
        steps.append(f"Have {finding.owner_role} investigate: {finding.title}.")
    steps.append("Use Recovery Center if the run is stale, not a destructive Clear.")
    return steps[:5]


def format_lead_checkin_message(
    findings: list[LeadCheckinFinding],
    assigned: list[object],
) -> str:
    lines = [
        f"{CHECKIN_GOAL_PREFIX} scheduled team health pass.",
        f"Findings: {len(findings)} · Assignments created: {len(assigned)}",
        "",
    ]
    for index, finding in enumerate(findings[:12], start=1):
        flag = "ESCALATE" if finding.escalate_only else f"→ {finding.owner_role}"
        lines.append(f"{index}. [{finding.kind}] {finding.title} ({flag})")
        if finding.detail:
            lines.append(f"   {humanize_lead_failure_detail(finding.detail)}")
    if not findings:
        lines.append("No failed shifts or degraded third-party signals this pass.")
    steps = _next_steps(findings)
    lines.extend(["", "## Next steps"])
    for index, step in enumerate(steps, start=1):
        lines.append(f"{index}. {step}")
    return "\n".join(lines).rstrip() + "\n"
