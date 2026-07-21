"""Plain-English alert explainers for a layman operator (VAXON handles the jargon)."""

from __future__ import annotations

import re
from typing import Any

BOOTSTRAP_SUMMARY_SIGNAL_IDS = frozenset(
    {
        "signal_runtime_summary_degraded",
        "signal_watch_bootstrap_ready",
    }
)


def is_bootstrap_summary_signal(signal_id: str, title: str) -> bool:
    lowered = title.lower()
    return (
        signal_id in BOOTSTRAP_SUMMARY_SIGNAL_IDS
        or "bootstrap" in lowered
        or "runtime summary stale" in lowered
    )


def _workspace_label(meta: dict[str, Any] | None) -> str:
    if not isinstance(meta, dict):
        return "this project"
    from_meta = str(meta.get("workspace_label") or "").strip()
    if from_meta:
        return from_meta
    workspace_id = str(meta.get("workspace_id") or "").strip()
    if not workspace_id:
        return "this project"
    return workspace_id.removeprefix("workspace_").replace("_", " ")


def _looks_like_connector(title: str, signal_id: str) -> bool:
    hay = f"{title} {signal_id}".lower()
    return bool(
        re.search(r"\bconnectors?\b", hay)
        or re.search(r"\bunavailable\b", hay)
        or re.search(r"\bunreachable\b", hay)
        or re.search(r"\boffline\b", hay)
        or "connector" in signal_id.lower()
    )


def _looks_like_auth_or_vault(title: str, summary: str) -> bool:
    hay = f"{title} {summary}".lower()
    return bool(
        re.search(r"\bvault\b", hay)
        or re.search(r"\bcredentials?\b", hay)
        or re.search(r"\bapi[_ ]?keys?\b", hay)
        or re.search(r"\bunauthorized\b", hay)
        or re.search(r"\bauth(entication|orization)?\b", hay)
        or re.search(r"\b(access )?tokens?\b", hay)
    )


def _looks_like_runtime_usage(title: str, summary: str) -> bool:
    hay = f"{title} {summary}".lower()
    return bool(
        re.search(r"\bout of usage\b", hay)
        or re.search(r"\busage limit\b", hay)
        or re.search(r"\brate limits?\b", hay)
        or re.search(r"\bquota\b", hay)
        or re.search(r"\bactionrequired\b", hay)
    )


def _looks_like_degraded(title: str, summary: str, signal_id: str) -> bool:
    hay = f"{title} {summary} {signal_id}".lower()
    return bool(
        re.search(r"\bdegraded\b", hay)
        or re.search(r"\bstale\b", hay)
        or re.search(r"\bunhealthy\b", hay)
    )


def _meta_plain_override(meta: dict[str, Any] | None) -> dict[str, str] | None:
    if not isinstance(meta, dict):
        return None
    what = str(meta.get("operator_what") or meta.get("plain_english") or "").strip()
    you_do = str(meta.get("operator_you_do") or meta.get("recommended_detail") or "").strip()
    agent_do = str(meta.get("operator_agent_do") or "").strip()
    spoken = str(meta.get("operator_spoken") or "").strip()
    if not (what or you_do or agent_do):
        return None
    out: dict[str, str] = {}
    if what:
        out["what"] = what
    if you_do:
        out["you_do"] = you_do
    if agent_do:
        out["agent_do"] = agent_do
    if spoken:
        out["spoken"] = spoken
    return out


def explain_operator_alert(
    *,
    signal_id: str = "",
    title: str = "",
    summary: str = "",
    meta: dict[str, Any] | None = None,
    pending_approvals: int = 0,
    reason: str = "",
) -> dict[str, str]:
    """Return what / you_do / agent_do / spoken for an operator alert."""
    signal_id = str(signal_id or "").strip()
    title = str(title or "").strip() or "Attention item"
    summary = str(summary or "").strip()
    meta = meta if isinstance(meta, dict) else None
    family = str((meta or {}).get("signal_family") or "").strip()
    pending = max(0, int(pending_approvals or 0))
    reason = str(reason or "").strip()

    if reason == "operator_approval_required" or pending > 0:
        count = pending if pending > 0 else 1
        noun = "one agent job" if count == 1 else f"{count} agent jobs"
        verb = "is" if count == 1 else "are"
        spoken = (
            "One job is waiting for your yes or no before I continue."
            if count == 1
            else f"{count} jobs are waiting for your yes or no before I continue."
        )
        return {
            "what": f"{noun} {verb} paused and waiting for your go-ahead.",
            "you_do": (
                "Open Approvals, read the short summary, then tap Approve "
                "(let it continue) or Reject (stop it)."
            ),
            "agent_do": (
                "Do not continue until the operator approves. After approval, resume "
                "the paused run and finish the original task. After reject, stop cleanly "
                "and leave a short note of what was cancelled."
            ),
            "spoken": spoken,
        }

    if family == "email_triage":
        sender = str((meta or {}).get("sender") or "someone").strip() or "someone"
        action = str((meta or {}).get("recommended_action") or "follow up").replace("_", " ")
        return {
            "what": f"An email from {sender} needs a human decision ({action}).",
            "you_do": (
                "Open Attention, skim the email thread, then hand it to the agent "
                "if you want a draft reply or investigation."
            ),
            "agent_do": (
                f"Triage the email from {sender}. Draft a reply or investigate the "
                "request, then pause for the operator to send or approve."
            ),
            "spoken": f"Email from {sender} needs a quick look.",
        }

    if family == "child_project_monitor":
        label = _workspace_label(meta)
        status = str((meta or {}).get("monitor_status") or "a warning").strip() or "a warning"
        return {
            "what": (
                f"{label} raised {status} on an outside service it watches "
                "(for example errors or downtime)."
            ),
            "you_do": (
                "Open the project’s Attention details. If it mentions missing keys, "
                "unlock Vault and add the credentials. Otherwise hand it to the agent."
            ),
            "agent_do": (
                f"Investigate the {label} monitor alert ({status}). Check the linked "
                "service dashboard, confirm whether it is a real outage or a config gap, "
                "fix what is safe, and report back in plain English."
            ),
            "spoken": f"{label} needs attention — something outside the app looked unhealthy.",
        }

    override = _meta_plain_override(meta)
    if (
        override
        and override.get("what")
        and override.get("you_do")
        and override.get("agent_do")
    ):
        spoken = override.get("spoken") or f"Heads up — {title}."
        return {
            "what": override["what"],
            "you_do": override["you_do"],
            "agent_do": override["agent_do"],
            "spoken": spoken,
        }

    if signal_id.startswith("signal_connector_") or _looks_like_connector(title, signal_id):
        project = _workspace_label(meta)
        return {
            "what": f"A connection Axon needs for {project} is down or not answering.",
            "you_do": (
                "Check that the related service is running, then ask the agent to re-check. "
                "If it keeps failing, open Vault for missing credentials."
            ),
            "agent_do": (
                f'Diagnose why the connector for "{title}" is unavailable. Verify the service '
                "is up, credentials are valid, and restore the link. Explain the fix in plain English."
            ),
            "spoken": "A connection Axon needs is down — I can help get it back.",
        }

    if is_bootstrap_summary_signal(signal_id, title):
        return {
            "what": (
                "This is a normal “still warming up” note in local development — "
                "not a production outage."
            ),
            "you_do": "You can ignore it, or keep using Command as usual. No repair step is required.",
            "agent_do": (
                "Do not treat this as an incident. Confirm Watch is connected, then "
                "continue with the operator’s real request."
            ),
            "spoken": "Just a warm-up note — nothing broken on your side.",
        }

    if _looks_like_runtime_usage(title, summary):
        return {
            "what": "The coding agent could not start because its usage limit or login is blocked.",
            "you_do": "Open Runtime / Vault, switch model or top up Cursor usage, then retry the job.",
            "agent_do": (
                "Do not retry blindly. Tell the operator which runtime is blocked and the "
                "exact fix (usage, login, or model switch), then wait for them."
            ),
            "spoken": "The agent could not start — usage or login needs a quick fix first.",
        }

    if _looks_like_auth_or_vault(title, summary):
        return {
            "what": "A locked vault or missing key is stopping a connected service from working.",
            "you_do": "Open Vault, unlock it, and make sure the needed key is present. Then retry.",
            "agent_do": (
                "Identify which key or unlock step is missing. Guide the operator to Vault; "
                "do not invent secrets. After unlock, re-check the failing connection."
            ),
            "spoken": "A key or vault unlock is needed before this can continue.",
        }

    if _looks_like_degraded(title, summary, signal_id):
        return {
            "what": (
                "Part of the system is running in a weaker “degraded” mode — "
                "some status may be incomplete."
            ),
            "you_do": (
                "Glance at the status strip. If something you need looks wrong, hand it "
                "to the agent; otherwise you can keep working."
            ),
            "agent_do": (
                f'Explain the degraded condition for "{title}" in plain English, list what '
                "still works, and fix or restart the unhealthy piece if it is safe."
            ),
            "spoken": "Something is running in a weaker mode — worth a quick look, not a panic.",
        }

    detail = summary if summary and summary.lower() != title.lower() else title
    clean_title = title
    if clean_title.upper().startswith("VAXON:"):
        clean_title = clean_title.split(":", 1)[1].strip() or title
    severity = str((meta or {}).get("severity") or "").strip().lower()
    severity_hint = (
        "This looks urgent."
        if severity in {"critical", "high"}
        else "This may be informational."
    )
    what = (override or {}).get("what") or f"Axon flagged something that needs a look: {detail}"
    you_do = (override or {}).get("you_do") or (
        "Open Attention Details for the plain-English guide. "
        f"{severity_hint} Then Approve, hand off to the agent, or Clear if it is noise."
    )
    agent_do = (override or {}).get("agent_do") or (
        f'Investigate "{title}". Do not assume a category — read the signal summary and meta, '
        "summarize in plain English for a non-technical operator, fix only what is safe, "
        "and say exactly what changed."
    )
    spoken = (override or {}).get("spoken") or f"Heads up — {clean_title}."
    return {
        "what": what,
        "you_do": you_do,
        "agent_do": agent_do,
        "spoken": spoken,
    }


def format_operator_alert_hint(explained: dict[str, str]) -> str:
    return (
        f"What happened: {explained['what']} "
        f"What you should do: {explained['you_do']} "
        f"What the agent should do: {explained['agent_do']}"
    )
