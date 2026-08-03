"""Template reply candidate pools for grounded KAIRO conversation replies."""

from __future__ import annotations

from typing import Any

def approval_candidates(facts: dict[str, Any], *, followup: bool) -> list[str]:
    pending = int(facts["pending_approvals"])
    prefix = "Still " if followup else ""
    if pending <= 0:
        return [
            f"{prefix}Nothing is waiting for your yes or no — you're clear.".strip(),
            f"{prefix}No jobs need a sign-off right now.".strip(),
            f"{prefix}Approval queue is empty on my side.".strip(),
        ]
    noun = "job" if pending == 1 else "jobs"
    return [
        f"{prefix}{pending} {noun} waiting for your yes or no — open Approvals first.".strip(),
        f"{prefix}You have {pending} paused {noun} that need Approve or Reject.".strip(),
        f"{prefix}{pending} {noun} on the board — Approvals has the simple next step.".strip(),
    ]


def attention_candidates(facts: dict[str, Any], *, followup: bool) -> list[str]:
    prefix = "Still " if followup else ""
    parts: list[str] = []
    pending = int(facts["pending_approvals"])
    if pending > 0:
        noun = "job" if pending == 1 else "jobs"
        parts.append(f"{pending} {noun} waiting for your yes or no")
    if facts["top_signal_title"]:
        detail = facts["top_signal_title"]
        if facts["top_signal_summary"]:
            detail = f"{detail} — {facts['top_signal_summary']}"
        parts.append(f"attention item is {detail}")
    elif int(facts["active_run_count"]) > 0:
        run_label = facts["primary_run_summary"] or "an active run"
        phase = facts["primary_run_phase"]
        if phase:
            parts.append(f"{run_label} is {phase.replace('_', ' ')}")
        else:
            parts.append(run_label)
    if not parts:
        return [
            f"{prefix}Nothing urgent — things look calm from here.".strip(),
            f"{prefix}All quiet — nothing I'd interrupt you for.".strip(),
        ]
    joined = "; ".join(parts)
    return [
        f"{prefix}Here's what needs you: {joined}.".strip(),
        f"{prefix}I'd start with {parts[0]}.".strip(),
        f"{prefix}Open Attention for the plain-English next step on: {joined}.".strip(),
    ]


def signal_candidates(facts: dict[str, Any], *, followup: bool) -> list[str]:
    prefix = "Still " if followup else ""
    if not facts["top_signal_title"]:
        return [
            f"{prefix}Inbox is quiet — nothing worth interrupting you for.".strip(),
            f"{prefix}No monitor or inbox fires right now.".strip(),
        ]
    title = facts["top_signal_title"]
    summary = facts["top_signal_summary"]
    severity = facts["top_signal_severity"]
    if summary:
        lines = [
            f"{prefix}Heads up — {title}: {summary}. Open Attention for what to do.".strip(),
            f"{prefix}I'd look at {title} next: {summary}".strip(),
        ]
        if severity:
            lines.append(
                f"{prefix}{severity.title()} alert: {title} — {summary}. "
                "I can explain the fix in plain English.".strip()
            )
        return lines
    return [
        f"{prefix}Heads up — {title}. Open Attention for what you and the agent should do.".strip(),
        f"{prefix}I'd review {title} first.".strip(),
    ]


def run_candidates(facts: dict[str, Any], *, followup: bool) -> list[str]:
    prefix = "Still " if followup else ""
    count = int(facts["active_run_count"])
    if count <= 0:
        return [
            f"{prefix}No active runs in flight right now.".strip(),
            f"{prefix}Run queue is idle on my side.".strip(),
        ]
    summary = facts["primary_run_summary"] or "an operator task"
    phase = facts["primary_run_phase"].replace("_", " ")
    suffix = "" if count == 1 else "s"
    if phase:
        lines = [
            f"{prefix}{count} active run{suffix} — lead item is {summary} ({phase}).".strip(),
        ]
        if count > 1:
            lines.append(f"{prefix}{summary} is {phase}; {count - 1} other run(s) behind it.".strip())
        else:
            lines.append(f"{prefix}{summary} is {phase}.".strip())
        return lines
    return [f"{prefix}{count} active run{suffix}; lead item is {summary}.".strip()]


def activity_candidates(facts: dict[str, Any], *, followup: bool) -> list[str]:
    prefix = "Still " if followup else ""
    workspace = facts["workspace_label"] or "that workspace"
    parts: list[str] = []
    if int(facts["active_run_count"]) > 0:
        run_label = facts["primary_run_summary"] or "an active run"
        phase = facts["primary_run_phase"]
        if phase:
            parts.append(f"latest run is {run_label} ({phase.replace('_', ' ')})")
        else:
            parts.append(f"latest run is {run_label}")
    if facts["top_signal_title"]:
        detail = facts["top_signal_title"]
        if facts["top_signal_summary"]:
            detail = f"{detail} — {facts['top_signal_summary']}"
        parts.append(f"top signal is {detail}")
    if not parts:
        return [
            f"{prefix}{workspace} looks quiet from here — no fresh runs or signals surfaced.".strip(),
            f"{prefix}I do not see recent activity in {workspace} worth flagging.".strip(),
        ]
    joined = "; ".join(parts)
    return [
        f"{prefix}In {workspace}, {joined}.".strip(),
        f"{prefix}{workspace} most recently shows this: {joined}.".strip(),
    ]


def runtime_candidates(facts: dict[str, Any], *, followup: bool) -> list[str]:
    prefix = "Still " if followup else ""
    if facts["cli_dispatch_ready"]:
        return [
            f"{prefix}CLI runtime looks dispatch-ready from my side.".strip(),
            f"{prefix}Local CLI auth looks good — agent dispatch should be available.".strip(),
        ]
    blockers = facts["cli_blockers"]
    lead = blockers[0] if blockers else "no local CLI runtime is dispatch-ready"
    return [
        f"{prefix}Not nominal — agent dispatch is blocked: {lead}.".strip(),
        f"{prefix}CLI runtime is not ready — {lead}. Open Runtime or /vault, then retry.".strip(),
        f"{prefix}I cannot start Lane B agents right now — {lead}.".strip(),
    ]


def health_candidates(facts: dict[str, Any], *, followup: bool) -> list[str]:
    prefix = "Still " if followup else ""
    if not facts["cli_dispatch_ready"]:
        blockers = facts["cli_blockers"]
        lead = blockers[0] if blockers else "CLI runtime is not dispatch-ready"
        return [
            f"{prefix}No — agent dispatch is blocked: {lead}.".strip(),
            f"{prefix}Not nominal — {lead}.".strip(),
        ]
    note = ""
    if facts["degraded"]:
        note = " Public tunnel health is degraded, but local control-plane is up — local work can continue."
    pending = int(facts["pending_approvals"])
    if pending > 0:
        noun = "job" if pending == 1 else "jobs"
        return [
            f"{prefix}Not fully clear — {pending} {noun} waiting for your yes or no.{note}".strip(),
        ]
    severity = facts["top_signal_severity"]
    if facts["top_signal_title"] and severity in {"high", "critical"}:
        return [
            f"{prefix}Mostly fine, but heads up on {facts['top_signal_title']}.{note}".strip(),
        ]
    review_ready = int(facts.get("review_ready_count") or 0)
    if review_ready > 0:
        suffix = "" if review_ready == 1 else "s"
        return [
            f"{prefix}CLI is ready, but {review_ready} run{suffix} still need review in Mission Control.{note}".strip(),
        ]
    if int(facts["active_run_count"]) > 0:
        return [
            f"{prefix}Yes — operational with {facts['active_run_count']} active run(s).{note}".strip(),
        ]
    if facts["degraded"]:
        return [
            f"{prefix}Local systems are up; public tunnel health is degraded — local charters and IDE work can proceed.{note}".strip(),
            f"{prefix}Not fully green publicly, but I'm operational locally — ready for your next order.{note}".strip(),
        ]
    return [
        f"{prefix}Yes — systems look nominal from my side.".strip(),
        f"{prefix}All clear here — CLI runtime is ready and nothing urgent is flagged.".strip(),
    ]


def fleet_candidates(facts: dict[str, Any], *, followup: bool) -> list[str]:
    prefix = "Still " if followup else ""
    critical = int(facts["critical_workspaces"])
    attention = int(facts["attention_workspaces"])
    total = int(facts["workspace_count"])
    tunnel_note = (
        " Public tunnel is degraded (local fleet still operable)."
        if facts["degraded"]
        else ""
    )
    if critical > 0:
        suffix = "" if critical == 1 else "s"
        return [
            f"{prefix}{critical} workspace{suffix} in critical state across {total} bound — I'd start there.{tunnel_note}".strip(),
            f"{prefix}Fleet scan: {critical} critical workspace{suffix} need you.{tunnel_note}".strip(),
        ]
    if attention > 0:
        suffix = "" if attention == 1 else "s"
        return [
            f"{prefix}{attention} workspace{suffix} need attention; nothing critical — want me to prioritize?{tunnel_note}".strip(),
            f"{prefix}Fleet is stable-ish — {attention} workspace{suffix} flagged.{tunnel_note}".strip(),
        ]
    suffix = "" if total == 1 else "s"
    if facts["advise"]:
        return [
            f"{prefix}Fleet looks healthy across {total} workspace{suffix}. Next: {facts['advise']}{tunnel_note}".strip(),
        ]
    if facts["degraded"]:
        return [
            f"{prefix}Fleet is operable locally across {total} workspace{suffix}; public tunnel health is degraded — I can still take charters.{tunnel_note}".strip(),
        ]
    return [
        f"{prefix}Fleet nominal — {total} workspace{suffix} look healthy. I'm watching; say if you want a deeper pass.".strip(),
        f"{prefix}Bound workspaces look green from here — standing by.".strip(),
    ]


def general_candidates(facts: dict[str, Any], *, followup: bool) -> list[str]:
    """Conversational second-brain brief — never semicolon dumps."""
    return status_report_candidates(facts, followup=followup)


def school_operations_candidates(facts: dict[str, Any], *, followup: bool) -> list[str]:
    """Useful Ask-mode fallback for centre/school operating-model advice."""
    workspace = str(facts.get("workspace_label") or "").strip().lower()
    lead = "Imani" if "young eagles" in workspace else "the school lead"
    return [
        (
            f"Yes — {lead} can help coordinate the operating rhythm, but we should set it up "
            "as a supervised school workflow, not a magic inbox. The useful first four lanes are "
            "daily homework, rubric-assisted marking with teacher sign-off, weekly parent updates, "
            "and practice assessments. Child reports, parent messages, and aftercare records need "
            "approved data, templates, permissions, and escalation rules before anything is sent. "
            "For Young Eagles and the wider school programme, I would also bring the EDP Excellence "
            "lead into the conversation so the handoff is explicit. In Ask mode, we can shape the "
            "operating model first; nothing is dispatched until you choose to make it a mission."
        ),
    ]


def status_report_candidates(facts: dict[str, Any], *, followup: bool) -> list[str]:
    """Categorized JARVIS-style stand-up in plain English."""
    prefix = "Still on it — " if followup else ""
    attention_bits: list[str] = []
    work_bits: list[str] = []
    next_bits: list[str] = []

    pending = int(facts["pending_approvals"])
    if pending > 0:
        noun = "approval" if pending == 1 else "approvals"
        attention_bits.append(f"{pending} {noun} waiting for your yes or no")

    notice = str(facts.get("notice") or "").strip().rstrip(".")
    if notice:
        attention_bits.append(notice)

    if facts["top_signal_title"]:
        title = str(facts["top_signal_title"]).strip()
        severity = str(facts.get("top_signal_severity") or "").strip().lower()
        if severity in {"high", "critical"}:
            attention_bits.append(f"the loud one is {title}")
        else:
            attention_bits.append(f"inbox is waving {title}")

    if facts["degraded"]:
        attention_bits.append("public tunnel health is soft, but local control is up")

    active = int(facts["active_run_count"])
    if active > 0:
        summary = facts["primary_run_summary"] or "a live run"
        phase = str(facts.get("primary_run_phase") or "").replace("_", " ").strip()
        if phase:
            work_bits.append(f"{summary} is {phase}")
        else:
            work_bits.append(f"{summary} is in flight")
        if active > 1:
            work_bits.append(f"{active - 1} more run{'s' if active > 2 else ''} behind it")

    review_ready = int(facts.get("review_ready_count") or 0)
    if review_ready > 0:
        work_bits.append(
            f"{review_ready} run{'s' if review_ready != 1 else ''} ready for your review"
        )

    advise = str(facts.get("advise") or "").strip().rstrip(".")
    if advise:
        next_bits.append(advise)
    elif facts["top_signal_title"]:
        next_bits.append(f"I'd open Attention and inspect {facts['top_signal_title']}")
    elif pending > 0:
        next_bits.append("I'd clear Approvals before starting anything new")
    elif not facts["cli_dispatch_ready"]:
        blockers = facts.get("cli_blockers") or []
        lead = blockers[0] if blockers else "CLI runtime is not dispatch-ready"
        next_bits.append(f"I'd unblock agent dispatch first — {lead}")
    else:
        next_bits.append("Nothing urgent — I can roll the fleet, check DashPro, or take your next order")

    if not attention_bits and not work_bits:
        return [
            (
                f"{prefix}Quiet board, sir. Systems look nominal from here. "
                f"{next_bits[0]}."
            ).strip(),
            (
                f"{prefix}Nothing I'd interrupt you for. "
                f"{next_bits[0]}."
            ).strip(),
        ]

    attention = (
        f"Attention: {', '.join(attention_bits[:3])}."
        if attention_bits
        else "Attention: nothing screaming."
    )
    work = (
        f" Work in flight: {', '.join(work_bits[:3])}."
        if work_bits
        else " Work in flight: idle."
    )
    nxt = f" Next: {next_bits[0]}."
    body = f"{attention}{work}{nxt}"
    return [
        f"{prefix}Here's the stand-up. {body}".strip(),
        f"{prefix}Quick second-brain pass. {body}".strip(),
        f"{prefix}Plain English, sir — {body}".strip(),
    ]


CANDIDATE_BUILDERS = {
    "approvals": approval_candidates,
    "attention": attention_candidates,
    "signals": signal_candidates,
    "runs": run_candidates,
    "activity": activity_candidates,
    "fleet": fleet_candidates,
    "runtime": runtime_candidates,
    "health": health_candidates,
    "school_operations": school_operations_candidates,
    "degraded": lambda f, *, followup: general_candidates(f, followup=followup),
    "status_report": status_report_candidates,
    "general": general_candidates,
    "followup": general_candidates,
}

__all__ = ["CANDIDATE_BUILDERS"]
