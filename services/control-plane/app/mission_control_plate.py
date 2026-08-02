"""Mission Control plate snapshot — Waiting / live / needs-attention / cross-ws."""

from __future__ import annotations

from typing import Any


def collect_mission_control_plate(
    *,
    focused_workspace_id: str | None = None,
) -> dict[str, Any]:
    """Count the board plate VAXON must not call “clear” while work remains."""
    from app.persistence import autonomous_attention_store, task_store

    focused = str(focused_workspace_id or "").strip() or None
    waiting = 0
    in_progress = 0
    needs_attention = 0
    sample_titles: list[str] = []

    def _ingest(workspace_id: str | None) -> None:
        nonlocal waiting, in_progress, needs_attention
        for status, bucket in (
            ("open", "waiting"),
            ("leased", "in_progress"),
            ("failed", "needs_attention"),
        ):
            rows = task_store.list_tasks(
                workspace_id=workspace_id,
                status=status,
                limit=200,
            )
            count = len(rows)
            if bucket == "waiting":
                waiting += count
            elif bucket == "in_progress":
                in_progress += count
            else:
                needs_attention += count
            for row in rows[:2]:
                goal = str(row.get("goal") or "").strip()
                if goal and len(sample_titles) < 4:
                    sample_titles.append(goal if len(goal) <= 72 else f"{goal[:71].rstrip()}…")

    if focused:
        _ingest(focused)
    else:
        # Fleet scan — keep it bounded; UI focuses one company at a time.
        from app.workspace_agents.config_loader import load_workspace_agent_configs

        _configs, _defaults, companies, _staffing = load_workspace_agent_configs()
        for workspace_id in sorted(companies.keys())[:8]:
            _ingest(workspace_id)

    pending = autonomous_attention_store.list_pending_decisions(limit=100)
    pending_n = len(pending)

    cross_ws = 0
    try:
        from app.persistence import handoff_store

        list_fn = getattr(handoff_store, "list_open_handoffs", None) or getattr(
            handoff_store, "list_handoffs", None
        )
        if callable(list_fn):
            handoffs = list_fn(limit=100)
            for row in handoffs or []:
                status = str(row.get("status") or "").strip().lower()
                if status in {"completed", "cancelled", "rejected"}:
                    continue
                cross_ws += 1
    except Exception:
        cross_ws = 0

    total_open_plate = waiting + in_progress + needs_attention + pending_n + cross_ws
    load = "idle"
    if needs_attention >= 8 or waiting + in_progress >= 6 or pending_n >= 3:
        load = "critical"
    elif total_open_plate > 0:
        load = "busy"

    return {
        "waiting": waiting,
        "in_progress": in_progress,
        "needs_attention": needs_attention,
        "pending_approvals": pending_n,
        "cross_workspace": cross_ws,
        "total_open_plate": total_open_plate,
        "load": load,
        "sample_titles": sample_titles,
        "focused_workspace_id": focused,
    }


def advise_from_plate(
    plate: dict[str, Any],
    *,
    auto_on: bool,
) -> tuple[str, dict[str, Any] | None]:
    """Human CEO line when Lead plans are clear but the board is not."""
    waiting = int(plate.get("waiting") or 0)
    live = int(plate.get("in_progress") or 0)
    needs = int(plate.get("needs_attention") or 0)
    pending = int(plate.get("pending_approvals") or 0)
    cross = int(plate.get("cross_workspace") or 0)
    samples = list(plate.get("sample_titles") or [])
    tip = f" Next: “{samples[0]}”." if samples else ""

    needs_label = (
        f"{needs} need review"
        if needs <= 40
        else f"{needs} failures queued for review"
    )
    if waiting > 0:
        line = (
            f"{waiting} Waiting start"
            f"{'' if waiting == 1 else 's'} · {live} live"
            + (f" · {needs_label}" if needs else "")
            + "."
        )
        if auto_on:
            line = f"Board still active — {line} I should clear Waiting / failures, not idle.{tip}"
        else:
            line = f"Board still active — {line} Open Waiting or Needs attention.{tip}"
        return line, {
            "type": "focus_task_board",
            "workspace_id": plate.get("focused_workspace_id"),
            "focus_attention": True,
            "column": "waiting",
        }

    if needs > 0:
        line = f"{needs} failure{'s' if needs != 1 else ''} need review."
        if auto_on:
            line = f"Lead plans clear, but {line} I am attending the failure queue.{tip}"
        else:
            line = f"Lead plans clear, but {line} Open Needs attention.{tip}"
        return line, {
            "type": "focus_task_board",
            "workspace_id": plate.get("focused_workspace_id"),
            "focus_attention": True,
            "column": "needs_attention",
        }

    if pending > 0:
        line = f"{pending} Needs-you card{'s' if pending != 1 else ''} still gated."
        return (
            f"{'I am clearing' if auto_on else 'Open'} Approvals — {line}",
            {
                "type": "focus_attention",
                "workspace_id": plate.get("focused_workspace_id"),
                "focus_attention": True,
            },
        )

    if cross > 0:
        line = f"{cross} cross-workspace handoff{'s' if cross != 1 else ''} still open."
        return (
            f"{'I am routing' if auto_on else 'Open'} From other workspaces — {line}",
            {
                "type": "focus_task_board",
                "workspace_id": plate.get("focused_workspace_id"),
                "focus_attention": True,
                "column": "waiting",
            },
        )

    if live > 0:
        return (
            f"{live} specialist{'s' if live != 1 else ''} still running — watching live work.",
            {
                "type": "focus_task_board",
                "workspace_id": plate.get("focused_workspace_id"),
                "focus_attention": True,
                "column": "in_progress",
            },
        )

    return "", None


__all__ = ["advise_from_plate", "collect_mission_control_plate"]
