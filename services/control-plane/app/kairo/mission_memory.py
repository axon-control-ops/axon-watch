"""Cited mission memory + advise→confirm→handoff/task flows (Continuous VAXON Phase 6).

Safety:
- Live DTOs override memory.
- “Remember” is explicit; casual ambient speech never becomes durable mission memory.
- “Start working on X” becomes advise → proposed owner/task/risk → verbal confirmation →
  leased task or IDE handoff receipt. It never acts on the initial polite request.
"""

from __future__ import annotations

import re
import time
from typing import Any

from app.kairo.turn_memory import entity_context, remember_entities

_MISSION_TTL_SECONDS = 6 * 60 * 60

_REMEMBER_MISSION_RE = re.compile(
    r"\b(?:remember(?:\s+that)?|mission(?:\s+is)?|we(?:'re| are)\s+working\s+on)\b[:\s]+(.+)$",
    re.IGNORECASE,
)
_START_WORK_RE = re.compile(
    r"\b(?:(?:can|could|would)\s+you\s+)?(?:start|begin|get\s+started)\s+(?:working\s+)?(?:on|with)\b",
    re.IGNORECASE,
)
_WHY_HOW_RE = re.compile(r"\b(why|how|explain|what\s+does|tell\s+me\s+about)\b", re.IGNORECASE)
_CONFIRM_RE = re.compile(
    r"^(yes|yeah|yep|do it|confirm|go ahead|proceed|approved)\.?$",
    re.IGNORECASE,
)
_REJECT_RE = re.compile(
    r"^(no|nope|cancel|stop|never\s*mind|reject|don't|do not)\.?$",
    re.IGNORECASE,
)


def _now() -> float:
    return time.time()


def remember_cited_mission(
    session_id: str,
    *,
    mission: str,
    workspace_id: str = "",
    citation: str = "",
    ttl_seconds: int = _MISSION_TTL_SECONDS,
) -> dict[str, str]:
    cleaned = " ".join(str(mission or "").strip().split())
    if not cleaned:
        return {}
    expires_at = str(int(_now() + max(60, ttl_seconds)))
    remember_entities(
        session_id,
        mission=cleaned[:400],
        mission_workspace_id=str(workspace_id or "").strip(),
        mission_citation=str(citation or "").strip()[:240],
        mission_expires_at=expires_at,
        mission_source="explicit",
    )
    return entity_context(session_id)


def clear_mission(session_id: str) -> None:
    remember_entities(
        session_id,
        mission="",
        mission_workspace_id="",
        mission_citation="",
        mission_expires_at="",
        mission_source="",
        pending_mission_confirm="",
        pending_mission_task="",
        pending_mission_risk="",
    )


def active_mission(session_id: str, *, now: float | None = None) -> dict[str, str] | None:
    entity = entity_context(session_id)
    mission = str(entity.get("mission") or "").strip()
    if not mission:
        return None
    expires_raw = str(entity.get("mission_expires_at") or "").strip()
    if expires_raw.isdigit():
        if (now if now is not None else _now()) > int(expires_raw):
            clear_mission(session_id)
            return None
    return {
        "mission": mission,
        "workspace_id": str(entity.get("mission_workspace_id") or "").strip(),
        "citation": str(entity.get("mission_citation") or "").strip(),
        "source": str(entity.get("mission_source") or "").strip() or "explicit",
        "expires_at": expires_raw,
    }


def override_mission_with_live_dto(
    session_id: str,
    *,
    live_mission: str | None,
    live_workspace_id: str | None = None,
) -> dict[str, str] | None:
    """Live DTO wins over stored memory when the operator surface provides a mission."""
    cleaned = " ".join(str(live_mission or "").strip().split())
    if not cleaned:
        return active_mission(session_id)
    return remember_cited_mission(
        session_id,
        mission=cleaned,
        workspace_id=str(live_workspace_id or "").strip(),
        citation="live_dto",
    )


def maybe_capture_explicit_remember(session_id: str, content: str) -> dict[str, str] | None:
    match = _REMEMBER_MISSION_RE.search(str(content or "").strip())
    if not match:
        return None
    mission = match.group(1).strip(" .")
    if len(mission) < 4:
        return None
    return remember_cited_mission(session_id, mission=mission, citation="operator_remember")


def is_polite_work_request(content: str) -> bool:
    text = str(content or "").strip()
    if not text or _WHY_HOW_RE.search(text):
        return False
    return bool(_START_WORK_RE.search(text))


def propose_mission_action(
    session_id: str,
    content: str,
    *,
    workspace_id: str = "",
    confirm_ttl_seconds: int = 15 * 60,
) -> dict[str, Any] | None:
    """Advise-only proposal. Never creates a task or dispatches work."""
    if not is_polite_work_request(content):
        return None
    task = " ".join(content.strip().split())[:280]
    risk = "reversible_auto_or_confirm — no shared checkout edits without a lease"
    expires_at = str(int(_now() + max(60, confirm_ttl_seconds)))
    remember_entities(
        session_id,
        pending_mission_confirm="1",
        pending_mission_task=task,
        pending_mission_risk=risk,
        pending_mission_expires_at=expires_at,
        mission_workspace_id=str(workspace_id or "").strip(),
    )
    reply = (
        f"I can take that as a mission: {task}. "
        "I have not started work. Say confirm to open an IDE handoff or leased task proposal, "
        "or say cancel."
    )
    return {
        "kind": "advise_confirm",
        "reply": reply,
        "task": task,
        "risk": risk,
        "requires_confirmation": True,
        "action": None,
    }


def resolve_mission_confirmation(
    session_id: str,
    content: str,
) -> dict[str, Any] | None:
    entity = entity_context(session_id)
    if entity.get("pending_mission_confirm") != "1":
        return None
    trimmed = content.strip()
    if _REJECT_RE.match(trimmed):
        remember_entities(
            session_id,
            pending_mission_confirm="",
            pending_mission_task="",
            pending_mission_risk="",
            pending_mission_expires_at="",
        )
        return {
            "kind": "rejected",
            "reply": "Cancelled. No task was created.",
            "action": None,
        }
    expires_raw = str(entity.get("pending_mission_expires_at") or "").strip()
    if expires_raw.isdigit() and _now() > int(expires_raw):
        remember_entities(
            session_id,
            pending_mission_confirm="",
            pending_mission_task="",
            pending_mission_risk="",
            pending_mission_expires_at="",
        )
        return {
            "kind": "expired",
            "reply": "That confirmation expired. Ask me again if you still want the handoff.",
            "action": None,
        }
    if not _CONFIRM_RE.match(trimmed):
        return None

    task = str(entity.get("pending_mission_task") or "").strip() or "Continue the current mission"
    workspace_id = str(entity.get("mission_workspace_id") or "").strip()
    remember_entities(
        session_id,
        pending_mission_confirm="",
        pending_mission_expires_at="",
        mission=task[:400],
        mission_source="confirmed",
        mission_expires_at=str(int(_now() + _MISSION_TTL_SECONDS)),
        mission_citation="verbal_confirm",
    )
    # Handoff receipt only — never silent task create / commit / push.
    action: dict[str, Any] = {
        "type": "dispatch_command",
        "content": f"/ide handoff {task}" if not workspace_id else f"/ide handoff {workspace_id}: {task}",
    }
    return {
        "kind": "confirmed_handoff",
        "reply": (
            "Confirmed. Opening an IDE handoff receipt for that mission. "
            "I still will not edit a shared checkout without a lease."
        ),
        "action": action,
        "task": task,
        "workspace_id": workspace_id,
    }


def mission_memory_appendix(session_id: str, *, max_chars: int = 400) -> str:
    mission = active_mission(session_id)
    if not mission:
        return ""
    lines = [
        "Cited mission (non-authoritative; live DTOs override):",
        f"- Mission: {mission['mission']}",
    ]
    if mission.get("workspace_id"):
        lines.append(f"- Workspace: {mission['workspace_id']}")
    if mission.get("citation"):
        lines.append(f"- Citation: {mission['citation']}")
    appendix = "\n".join(lines)
    if len(appendix) <= max_chars:
        return appendix
    return appendix[: max(0, max_chars - 1)].rstrip() + "…"


__all__ = [
    "active_mission",
    "clear_mission",
    "is_polite_work_request",
    "maybe_capture_explicit_remember",
    "mission_memory_appendix",
    "override_mission_with_live_dto",
    "propose_mission_action",
    "remember_cited_mission",
    "resolve_mission_confirmation",
]
