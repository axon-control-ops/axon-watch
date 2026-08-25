"""Deterministic reminder / open-loop engine built on operator memories."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.persistence import operator_memory_store

WHATSAPP_G42_TITLE = "Revisit WhatsApp native slice (G4.2)"
WHATSAPP_G42_CONTENT_MARKER = "WhatsApp native slice"
WHATSAPP_G42_LEGACY_MARKERS = (
    "Revisit WhatsApp soft-cutover (G4.2)",
    "WhatsApp soft-cutover",
)


def _parse_iso(value: str | None) -> datetime | None:
    trimmed = str(value or "").strip()
    if not trimmed:
        return None
    try:
        if trimmed.endswith("Z"):
            trimmed = trimmed[:-1] + "+00:00"
        return datetime.fromisoformat(trimmed).astimezone(timezone.utc)
    except ValueError:
        return None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def promote_memory_to_reminder(
    memory_id: str,
    *,
    due_at: str,
    priority: str = "normal",
    trigger: str = "time",
) -> dict[str, Any] | None:
    return operator_memory_store.patch_memory(
        memory_id,
        {
            "kind": "reminder",
            "due_at": due_at,
            "priority": priority,
            "trigger": trigger,
            "status": "open",
            "snoozed_until": "",
            "dismiss_reason": "",
        },
    )


def patch_reminder(memory_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    allowed = {
        "due_at",
        "snoozed_until",
        "trigger",
        "priority",
        "status",
        "last_presented_at",
        "dismiss_reason",
        "kind",
        "title",
        "content",
    }
    clean = {key: value for key, value in patch.items() if key in allowed}
    if "status" in clean and clean["status"] == "snoozed" and not clean.get("snoozed_until"):
        clean["snoozed_until"] = (_utc_now() + timedelta(hours=4)).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        )
    return operator_memory_store.patch_memory(memory_id, clean)


def due_reminders(
    *,
    workspace_id: str | None = None,
    now: datetime | None = None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Return open reminders that should surface now (time or event triggers)."""
    clock = now or _utc_now()
    items = operator_memory_store.list_memories(
        workspace_id=workspace_id,
        kind=None,
        limit=50,
        include_reminders=True,
    )
    due: list[dict[str, Any]] = []
    for item in items:
        if str(item.get("kind") or "") not in {"reminder", "open_loop"}:
            continue
        status = str(item.get("status") or "open").lower()
        if status in {"done", "dismissed", "closed"}:
            continue
        snoozed_until = _parse_iso(str(item.get("snoozed_until") or ""))
        if snoozed_until and snoozed_until > clock:
            continue
        trigger = str(item.get("trigger") or "time").lower()
        due_at = _parse_iso(str(item.get("due_at") or ""))
        why_now = ""
        if trigger == "time":
            if due_at is None or due_at > clock:
                continue
            why_now = f"Due at {item.get('due_at')}"
        elif trigger == "event":
            # Event reminders surface when status is open and not snoozed;
            # callers attach event evidence separately.
            why_now = str(item.get("content") or "Event trigger open")
        else:
            if due_at is not None and due_at > clock:
                continue
            why_now = "Open loop ready for review"
        enriched = dict(item)
        enriched["why_now"] = why_now
        due.append(enriched)
        if len(due) >= max(1, min(20, int(limit or 8))):
            break
    return due


def list_open_loops(*, workspace_id: str | None = None, limit: int = 12) -> list[dict[str, Any]]:
    items = operator_memory_store.list_memories(
        workspace_id=workspace_id,
        kind=None,
        limit=max(1, min(50, int(limit or 12))),
        include_reminders=True,
    )
    return [
        item
        for item in items
        if str(item.get("kind") or "") in {"reminder", "open_loop"}
        and str(item.get("status") or "open").lower() not in {"done", "dismissed", "closed"}
    ]


def migrate_whatsapp_g42_reminder(*, due_hours: int = 24) -> dict[str, Any] | None:
    """Ensure the WhatsApp G4.2 operator memory is a real due reminder."""
    matches = operator_memory_store.search_memories("WhatsApp", workspace_id=None, limit=20)
    target = None
    for item in matches:
        title = str(item.get("title") or "")
        content = str(item.get("content") or "")
        haystack = f"{title}\n{content}".lower()
        markers = (WHATSAPP_G42_TITLE, WHATSAPP_G42_CONTENT_MARKER, *WHATSAPP_G42_LEGACY_MARKERS)
        if any(marker.lower() in haystack for marker in markers):
            target = item
            break
    due_at = (_utc_now() + timedelta(hours=max(1, int(due_hours)))).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )
    if target is None:
        created = operator_memory_store.create_memory(
            workspace_id="",
            scope="personal",
            kind="reminder",
            title=WHATSAPP_G42_TITLE,
            content=(
                "Revisit WhatsApp native slice (G4.2): decide when to build "
                "Axon-X WhatsApp monitoring without axon-local fallback."
            ),
            source_refs=[{"kind": "migration", "id": "whatsapp_g42"}],
            created_at=_utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            due_at=due_at,
            trigger="time",
            priority="high",
            status="open",
        )
        return created
    return operator_memory_store.patch_memory(
        str(target["memory_id"]),
        {
            "kind": "reminder",
            "due_at": str(target.get("due_at") or due_at),
            "trigger": "time",
            "priority": "high",
            "status": "open" if str(target.get("status") or "open") in {"", "open"} else target.get("status"),
            "title": WHATSAPP_G42_TITLE,
            "content": (
                "Revisit WhatsApp native slice (G4.2): decide when to build "
                "Axon-X WhatsApp monitoring without axon-local fallback."
            ),
        },
    )
