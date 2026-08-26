"""Fleet health projection for operator second-brain grid (OP-B1)."""

from __future__ import annotations

from app.inbox_projection import WatchInboxFetcher, build_inbox_response
from app.operator_briefing_signals import filter_actionable_inbox_items
from app.runs.service import list_operator_facing_active_runs
from app.runtime_summary_assembler import WatchProbe, assemble_runtime_summary
from app.workspace_catalog import list_workspace_records


def _health_tone(
    *,
    review_ready_count: int,
    executing_count: int,
    pending_approvals_count: int,
    open_signals_count: int,
    critical_signals_count: int,
) -> str:
    if pending_approvals_count > 0 or critical_signals_count > 0:
        return "critical"
    if review_ready_count > 0 or executing_count > 0 or open_signals_count > 0:
        return "attention"
    return "nominal"


def build_operator_fleet_health(
    *,
    watch_probe: WatchProbe | None = None,
    inbox_fetcher: WatchInboxFetcher | None = None,
) -> dict[str, object]:
    runtime_summary = assemble_runtime_summary(
        watch_probe=watch_probe,
        inbox_fetcher=inbox_fetcher,
    )
    watch_connected = bool(runtime_summary["watch"]["connected"])
    inbox_snapshot = (
        build_inbox_response(inbox_fetcher=inbox_fetcher, allow_empty_unavailable=True)
        if watch_connected
        else {"items": [], "count": 0, "updated_at": runtime_summary["generated_at"]}
    )
    inbox_items = [
        item for item in inbox_snapshot.get("items", []) if isinstance(item, dict)
    ]

    active_runs = list_operator_facing_active_runs()

    workspace_records = list_workspace_records(
        inbox_fetcher=inbox_fetcher,
        operator_surface=True,
    )
    items: list[dict[str, object]] = []

    for workspace in workspace_records:
        workspace_id = str(workspace["workspace_id"])
        display_name = str(workspace.get("display_name") or workspace_id)
        workspace_runs = [
            run for run in active_runs if str(run.get("workspace_id", "")) == workspace_id
        ]
        workspace_signals = filter_actionable_inbox_items(
            [
                signal
                for signal in inbox_items
                if str(signal.get("workspace_id", "")).strip() in {"", workspace_id}
                and signal.get("status") == "open"
            ]
        )
        review_ready_count = sum(
            1 for run in workspace_runs if run.get("phase") == "review_ready"
        )
        executing_count = sum(1 for run in workspace_runs if run.get("phase") == "executing")
        pending_approvals_count = sum(
            1 for run in workspace_runs if run.get("phase") == "awaiting_approval"
        )
        critical_signals_count = sum(
            1
            for signal in workspace_signals
            if signal.get("severity") in {"critical", "high"}
        )
        top_signal = workspace_signals[0] if workspace_signals else None

        items.append(
            {
                "workspace_id": workspace_id,
                "display_name": display_name,
                "connection_kind": str(workspace.get("connection_kind", "isolated_root")),
                "health": _health_tone(
                    review_ready_count=review_ready_count,
                    executing_count=executing_count,
                    pending_approvals_count=pending_approvals_count,
                    open_signals_count=len(workspace_signals),
                    critical_signals_count=critical_signals_count,
                ),
                "active_runs": len(workspace_runs),
                "review_ready_count": review_ready_count,
                "executing_count": executing_count,
                "pending_approvals_count": pending_approvals_count,
                "open_signals_count": len(workspace_signals),
                "critical_signals_count": critical_signals_count,
                "top_signal_title": str(top_signal.get("title", "")) if top_signal else None,
            }
        )

    return {
        "generated_at": runtime_summary["generated_at"],
        "watch_connected": watch_connected,
        "connectors": runtime_summary["connectors"],
        "degraded": runtime_summary["degraded"],
        "items": items,
        "count": len(items),
    }
