"""Conversational reminder intents on top of the durable host reminder engine."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from app.host_context import reminders as reminder_engine
from app.persistence.operator_memory_store import create_memory, patch_memory

_REMIND_ME_RE = re.compile(
    r"^(?:remind me(?: to)?|set a reminder(?: to)?)\s+(.+)$",
    re.IGNORECASE,
)
_IN_DURATION_RE = re.compile(
    r"^(?P<body>.+?)\s+in\s+(?P<qty>\d+)\s*(?P<unit>minutes?|mins?|hours?|hrs?|days?)$",
    re.IGNORECASE,
)
_CONFIRM_RE = re.compile(r"^(?:yes|confirm|looks good|that'?s right)\b", re.IGNORECASE)
_SNOOZE_RE = re.compile(r"^snooze(?:\s+(?P<qty>\d+)\s*(?P<unit>minutes?|mins?|hours?|hrs?))?$", re.IGNORECASE)
_DISMISS_RE = re.compile(r"^(?:dismiss|cancel)(?:\s+reminder)?$", re.IGNORECASE)
_COMPLETE_RE = re.compile(r"^(?:done|complete|completed)(?:\s+reminder)?$", re.IGNORECASE)
_RECURRING_RE = re.compile(
    r"^(?P<body>.+?)\s+every\s+(?P<qty>\d+)\s*(?P<unit>hours?|hrs?|days?)$",
    re.IGNORECASE,
)

# Pending confirmation keyed by session (process-local; durable row created on confirm).
_PENDING: dict[str, dict[str, Any]] = {}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _delta(qty: int, unit: str) -> timedelta:
    normalized = unit.lower()
    if normalized.startswith("min"):
        return timedelta(minutes=qty)
    if normalized.startswith("hour") or normalized.startswith("hr"):
        return timedelta(hours=qty)
    return timedelta(days=qty)


def parse_reminder_request(
    content: str,
    *,
    timezone_name: str = "UTC",
    now: datetime | None = None,
) -> dict[str, Any] | None:
    match = _REMIND_ME_RE.match(str(content or "").strip())
    if not match:
        return None
    rest = match.group(1).strip()
    recurring = _RECURRING_RE.match(rest)
    duration = _IN_DURATION_RE.match(rest)
    clock = now or _utc_now()
    try:
        tz = ZoneInfo(timezone_name)
    except Exception:
        tz = timezone.utc
        timezone_name = "UTC"
    local_now = clock.astimezone(tz)

    if recurring:
        qty = int(recurring.group("qty"))
        unit = recurring.group("unit")
        body = recurring.group("body").strip(" ,.")
        due = local_now + _delta(qty, unit)
        return {
            "title": body[:72] or "Reminder",
            "content": body,
            "due_at": _iso(due),
            "timezone": timezone_name,
            "recurrence": {"every": qty, "unit": unit.lower()},
            "needs_confirmation": True,
        }
    if duration:
        qty = int(duration.group("qty"))
        unit = duration.group("unit")
        body = duration.group("body").strip(" ,.")
        due = local_now + _delta(qty, unit)
        return {
            "title": body[:72] or "Reminder",
            "content": body,
            "due_at": _iso(due),
            "timezone": timezone_name,
            "recurrence": None,
            "needs_confirmation": True,
        }
    # Default: remind in 1 hour when no explicit time parsed.
    due = local_now + timedelta(hours=1)
    return {
        "title": rest[:72] or "Reminder",
        "content": rest,
        "due_at": _iso(due),
        "timezone": timezone_name,
        "recurrence": None,
        "needs_confirmation": True,
    }


def stage_reminder_confirmation(session_id: str, parsed: dict[str, Any]) -> dict[str, Any]:
    _PENDING[session_id] = dict(parsed)
    when = parsed.get("due_at")
    tz = parsed.get("timezone") or "UTC"
    reply = (
        f"I can remind you about “{parsed.get('title')}” at {when} ({tz}). "
        "Say confirm to save it, or tell me a different time."
    )
    return {"reply": reply, "pending": parsed, "awaiting_confirmation": True}


def confirm_pending_reminder(
    session_id: str,
    *,
    workspace_id: str = "",
) -> dict[str, Any] | None:
    pending = _PENDING.pop(session_id, None)
    if not pending:
        return None
    record = create_memory(
        workspace_id=workspace_id,
        scope="workspace" if workspace_id else "personal",
        kind="reminder",
        title=str(pending.get("title") or "Reminder"),
        content=str(pending.get("content") or ""),
        source_refs=[{"ref_type": "conversation", "ref_id": session_id, "label": "remind_me"}],
        created_at=_iso(_utc_now()),
        due_at=str(pending.get("due_at") or ""),
        trigger="time",
        priority="normal",
        status="open",
    )
    if pending.get("recurrence"):
        patch_memory(
            str(record["memory_id"]),
            {"content": f"{record.get('content')} · recurrence={pending['recurrence']}"},
        )
    return {
        "reply": f"Saved. I’ll remind you about “{record.get('title')}” at {record.get('due_at')}.",
        "reminder": record,
    }


def maybe_handle_reminder_intent(
    *,
    content: str,
    session_id: str,
    workspace_id: str | None = None,
    timezone_name: str = "UTC",
) -> dict[str, Any] | None:
    text = str(content or "").strip()
    if not text:
        return None

    if _CONFIRM_RE.match(text) and session_id in _PENDING:
        confirmed = confirm_pending_reminder(session_id, workspace_id=str(workspace_id or ""))
        if confirmed:
            return {
                "turn_kind": "action",
                "reply": confirmed["reply"],
                "source": "template",
                "action": {"type": "reminder_created", "reminder": confirmed["reminder"]},
                "artifacts": [],
            }

    snooze = _SNOOZE_RE.match(text)
    if snooze:
        qty = int(snooze.group("qty") or 15)
        unit = snooze.group("unit") or "minutes"
        due = list(reminder_engine.due_reminders(workspace_id=workspace_id, limit=1))
        if not due:
            open_items = reminder_engine.list_open_loops(workspace_id=workspace_id, limit=1)
            due = open_items
        if not due:
            return {
                "turn_kind": "action",
                "reply": "I don’t have an open reminder to snooze.",
                "source": "template",
                "action": None,
                "artifacts": [],
            }
        target = due[0]
        until = _utc_now() + _delta(qty, unit)
        updated = reminder_engine.patch_reminder(
            str(target["memory_id"]),
            {"status": "snoozed", "snoozed_until": _iso(until)},
        )
        return {
            "turn_kind": "action",
            "reply": f"Snoozed “{target.get('title')}” until {updated and updated.get('snoozed_until')}.",
            "source": "template",
            "action": {"type": "reminder_snoozed", "reminder": updated},
            "artifacts": [],
        }

    if _DISMISS_RE.match(text) or _COMPLETE_RE.match(text):
        items = reminder_engine.list_open_loops(workspace_id=workspace_id, limit=1)
        if not items:
            return {
                "turn_kind": "action",
                "reply": "No open reminder to update.",
                "source": "template",
                "action": None,
                "artifacts": [],
            }
        status = "done" if _COMPLETE_RE.match(text) else "dismissed"
        updated = reminder_engine.patch_reminder(str(items[0]["memory_id"]), {"status": status})
        return {
            "turn_kind": "action",
            "reply": f"Marked “{items[0].get('title')}” as {status}.",
            "source": "template",
            "action": {"type": f"reminder_{status}", "reminder": updated},
            "artifacts": [],
        }

    parsed = parse_reminder_request(text, timezone_name=timezone_name)
    if not parsed:
        return None
    staged = stage_reminder_confirmation(session_id, parsed)
    return {
        "turn_kind": "action",
        "reply": staged["reply"],
        "source": "template",
        "action": {"type": "reminder_confirm_required", "pending": parsed},
        "artifacts": [],
    }


def clear_pending_for_tests() -> None:
    _PENDING.clear()
