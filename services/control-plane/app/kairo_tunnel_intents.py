"""VAXON early intent: restart / repair the public Cloudflare tunnel."""

from __future__ import annotations

import re
from typing import Any

from app.kairo_participant_memory import apply_participant_address, get_active_participant

_TUNNEL_REPAIR_RE = re.compile(
    r"\b("
    r"(?:fix|repair|restart|restore|bring\s+up|spin\s+up|start|re-?enable)\s+"
    r"(?:the\s+)?(?:public\s+)?(?:cloudflare\s+)?(?:tunnel|remote\s+ingress|ingress)"
    r"|"
    r"(?:public\s+tunnel|remote\s+ingress|cloudflare\s+tunnel)\s+"
    r"(?:is\s+)?(?:down|soft|broken|degraded|unreachable|dead)"
    r"|"
    r"tunnel\s+(?:please|now|again)"
    r")\b",
    re.IGNORECASE,
)


def detect_public_tunnel_repair_intent(content: str) -> bool:
    return bool(_TUNNEL_REPAIR_RE.search(str(content or "")))


def _status_ok(payload: dict[str, Any] | None) -> bool:
    if not isinstance(payload, dict):
        return False
    if payload.get("running") is True:
        return True
    status = str(payload.get("status") or "").strip().lower()
    return status in {"ok", "running", "active", "healthy"}


def maybe_handle_public_tunnel_repair_intent(
    *,
    content: str,
    session_id: str,
    guest_name: str | None,
) -> dict[str, Any] | None:
    if not detect_public_tunnel_repair_intent(content):
        return None

    from app.adapters.watch_client import fetch_watch_tunnel, post_watch_tunnel_action

    participant = guest_name or get_active_participant(session_id)
    before = fetch_watch_tunnel(timeout_seconds=2.0)
    started = post_watch_tunnel_action("start", timeout_seconds=90.0)
    after = fetch_watch_tunnel(timeout_seconds=3.0) or started

    if started is None and not _status_ok(after):
        reply = (
            "I tried to restart the public tunnel, but Watch did not accept the start command. "
            "Local Axon-X is still up — open Connectors and tap Start tunnel, or run "
            "axonfixconnectors on the host."
        )
        outcome = "watch_unavailable"
    elif _status_ok(after) or _status_ok(started):
        url = str((after or started or {}).get("url") or "https://axon.edudashpro.org.za").strip()
        detail = str((after or started or {}).get("detail") or "").strip()
        already = _status_ok(before)
        if already:
            reply = (
                f"Public tunnel was already up for {url}"
                f"{f' — {detail}' if detail else ''}. "
                "I re-issued start and refreshed health; local control stays unaffected."
            )
            outcome = "already_running"
        else:
            reply = (
                f"Restarted the public tunnel for {url}"
                f"{f' — {detail}' if detail else ''}. "
                "Remote ingress should clear once the next health probe lands."
            )
            outcome = "started"
    else:
        detail = str((started or after or {}).get("detail") or (started or after or {}).get("msg") or "").strip()
        reply = (
            "I sent the tunnel start command, but public ingress still looks soft"
            f"{f' ({detail})' if detail else ''}. "
            "Local stack is fine — check Cloudflare auth in Vault or run axonfixconnectors."
        )
        outcome = "start_soft"

    return {
        "turn_kind": "action",
        "reply": apply_participant_address(reply, participant),
        "source": "template",
        "command_content": None,
        "action": {
            "type": "start_tunnel",
            "outcome": outcome,
            "tunnel": after if isinstance(after, dict) else started,
        },
        "artifacts": [],
        "active_participant": participant,
        "action_tier": "reversible_auto",
    }
