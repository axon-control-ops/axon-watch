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
    if facts["degraded"]:
        return [
            f"{prefix}Not fully nominal — runtime is degraded.".strip(),
            f"{prefix}We're degraded — check watch/runtime health first.".strip(),
        ]
    pending = int(facts["pending_approvals"])
    if pending > 0:
        noun = "job" if pending == 1 else "jobs"
        return [
            f"{prefix}Not fully clear — {pending} {noun} waiting for your yes or no.".strip(),
        ]
    severity = facts["top_signal_severity"]
    if facts["top_signal_title"] and severity in {"high", "critical"}:
        return [
            f"{prefix}Mostly fine, but heads up on {facts['top_signal_title']}.".strip(),
        ]
    review_ready = int(facts.get("review_ready_count") or 0)
    if review_ready > 0:
        suffix = "" if review_ready == 1 else "s"
        return [
            f"{prefix}CLI is ready, but {review_ready} run{suffix} still need review in Mission Control.".strip(),
        ]
    if int(facts["active_run_count"]) > 0:
        return [
            f"{prefix}Yes — operational with {facts['active_run_count']} active run(s); nothing critical flagged.".strip(),
        ]
    return [
        f"{prefix}Yes — systems look nominal from my side.".strip(),
        f"{prefix}All clear here — CLI runtime is ready and nothing urgent is flagged.".strip(),
    ]


def fleet_candidates(facts: dict[str, Any], *, followup: bool) -> list[str]:
    prefix = "Still " if followup else ""
    if facts["degraded"]:
        return [
            f"{prefix}Fleet view is up, but runtime is degraded — I'd clear health before trusting green lights.".strip(),
            f"{prefix}Not clean yet — degraded runtime is the priority over workspace counts.".strip(),
        ]
    critical = int(facts["critical_workspaces"])
    attention = int(facts["attention_workspaces"])
    total = int(facts["workspace_count"])
    if critical > 0:
        suffix = "" if critical == 1 else "s"
        return [
            f"{prefix}{critical} workspace{suffix} in critical state across {total} bound — I'd start there.".strip(),
            f"{prefix}Fleet scan: {critical} critical workspace{suffix} need you.".strip(),
        ]
    if attention > 0:
        suffix = "" if attention == 1 else "s"
        return [
            f"{prefix}{attention} workspace{suffix} need attention; nothing critical — want me to prioritize?".strip(),
            f"{prefix}Fleet is stable-ish — {attention} workspace{suffix} flagged.".strip(),
        ]
    suffix = "" if total == 1 else "s"
    if facts["advise"]:
        return [
            f"{prefix}Fleet looks healthy across {total} workspace{suffix}. Next: {facts['advise']}".strip(),
        ]
    return [
        f"{prefix}Fleet nominal — {total} workspace{suffix} look healthy. I'm watching; say if you want a deeper pass.".strip(),
        f"{prefix}Bound workspaces look green from here — standing by.".strip(),
    ]


def general_candidates(facts: dict[str, Any], *, followup: bool) -> list[str]:
    prefix = "Still " if followup else ""
    if not facts["cli_dispatch_ready"]:
        blockers = facts["cli_blockers"]
        lead = blockers[0] if blockers else "CLI runtime is not dispatch-ready"
        return [
            f"{prefix}Not nominal on my side — {lead}. I'd fix that before new agent work.".strip(),
            f"{prefix}Agent dispatch is blocked — {lead}. Check Runtime or /vault.".strip(),
        ]
    if facts["degraded"]:
        return [
            f"{prefix}Runtime is degraded — I'd fix connectivity before dispatching more. Want me to walk it?".strip(),
            f"{prefix}We're in degraded mode — check watch/runtime health first.".strip(),
        ]
    chunks: list[str] = []
    if facts["notice"]:
        chunks.append(facts["notice"])
    if int(facts["pending_approvals"]) > 0:
        chunks.append(f"{facts['pending_approvals']} approval(s) waiting")
    if facts["top_signal_title"]:
        chunks.append(f"top signal {facts['top_signal_title']}")
    elif int(facts["active_run_count"]) > 0:
        chunks.append(f"{facts['active_run_count']} active run(s)")
    if facts["advise"] and facts["advise"] not in " ".join(chunks):
        chunks.append(facts["advise"])
    if not chunks:
        return [
            f"{prefix}All quiet on the board — I'm watching. Want a fleet rollup or shall we pick a workspace?".strip(),
            f"{prefix}Nothing urgent from my scan — I can brief leads, check DashPro CI, or take your next order.".strip(),
            f"{prefix}Systems look nominal — standing by like Jarvis. What shall we tackle?".strip(),
        ]
    body = "; ".join(chunks[:3])
    return [
        f"{prefix}{body}.".strip(),
        f"{prefix}Quick read: {body}.".strip(),
        f"{prefix}I'd act on this first — {body}.".strip(),
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
    "degraded": lambda f, *, followup: general_candidates(f, followup=followup),
    "general": general_candidates,
    "followup": general_candidates,
}

__all__ = ["CANDIDATE_BUILDERS"]
