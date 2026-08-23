"""Best-effort live-event notification after material run lifecycle changes."""

from __future__ import annotations

from typing import Any


def notify_run_material_change(run_id: str, record: dict[str, Any]) -> None:
    try:
        from app.live_events import broadcast_material_change

        broadcast_material_change(receipt_id=str(record.get("run_id") or run_id))
    except Exception:
        pass
    phase = str(record.get("phase") or "").strip()
    if phase == "completed":
        try:
            from app.workspace_agents.autonomous_attention_recovery import (
                reconcile_workspace_recovered_decisions,
            )

            reconcile_workspace_recovered_decisions(
                str(record.get("workspace_id") or ""),
                completed_run=record,
            )
        except Exception:
            pass
    try:
        from app.local_notifications import notify_run_transition

        notify_run_transition(record)
    except Exception:
        pass
