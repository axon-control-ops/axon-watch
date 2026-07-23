"""Policy-driven opportunistic / proactive speech (not uncontrolled randomness)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class SpeechBudget:
    max_interruptions_per_hour: int = 4
    spoken_in_window: int = 0
    window_started_at: str | None = None

    def allow(self) -> bool:
        return self.spoken_in_window < self.max_interruptions_per_hour

    def record(self, *, now: datetime | None = None) -> None:
        clock = now or datetime.now(timezone.utc)
        iso = clock.replace(microsecond=0).isoformat().replace("+00:00", "Z")
        if not self.window_started_at:
            self.window_started_at = iso
            self.spoken_in_window = 0
        self.spoken_in_window += 1


def choose_opportunistic_speech(
    *,
    due_reminders: list[dict[str, Any]],
    open_loops: list[dict[str, Any]],
    material_incidents: list[dict[str, Any]],
    budget: SpeechBudget,
    console_active: bool,
    quiet_hours: bool,
) -> dict[str, Any] | None:
    """Pick at most one spoken line when policy allows.

    Stage 1 delivery: only while desktop/console is active.
    """
    if not console_active or quiet_hours or not budget.allow():
        return None

    if due_reminders:
        item = due_reminders[0]
        budget.record()
        return {
            "kind": "reminder",
            "priority": str(item.get("priority") or "normal"),
            "text": f"Reminder: {item.get('title') or item.get('content')}",
            "memory_id": item.get("memory_id"),
            "channel": "desktop_active",
        }
    if material_incidents:
        incident = material_incidents[0]
        budget.record()
        return {
            "kind": "incident",
            "priority": "high",
            "text": f"Attention: {incident.get('message') or incident.get('summary')}",
            "channel": "desktop_active",
        }
    if open_loops:
        loop = open_loops[0]
        budget.record()
        return {
            "kind": "open_loop",
            "priority": "low",
            "text": f"Open loop: {loop.get('title') or loop.get('content')}",
            "memory_id": loop.get("memory_id"),
            "channel": "desktop_active",
        }
    return None
