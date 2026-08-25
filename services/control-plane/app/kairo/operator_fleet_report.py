"""Fleet-wide workspace evidence for deterministic VAXON reports."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.kairo.report_text import _scrub_operator_line


def live_fleet_health(fleet: dict[str, Any]) -> dict[str, Any]:
    """Expand a count-only context pack into live fleet items for REPORT."""
    if isinstance(fleet.get("items"), list):
        return fleet
    try:
        from app.operator_fleet_health import build_operator_fleet_health

        return build_operator_fleet_health()
    except Exception:
        return dict(fleet)


def collect_workspace_reports(
    *,
    fleet: dict[str, Any],
    scoped_workspace_id: str,
    scoped_roster: dict[str, Any],
    scoped_handoffs: list[dict[str, Any]],
    roster_loader: Callable[[str], dict[str, Any]],
    handoff_loader: Callable[[str], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for item in fleet.get("items", []):
        if not isinstance(item, dict):
            continue
        workspace_id = str(item.get("workspace_id") or "").strip()
        if not workspace_id:
            continue
        roster = scoped_roster if workspace_id == scoped_workspace_id else roster_loader(workspace_id)
        handoffs = (
            scoped_handoffs if workspace_id == scoped_workspace_id else handoff_loader(workspace_id)
        )
        active_runs = int(item.get("active_runs") or 0)
        has_reportable_evidence = bool(
            roster.get("busy")
            or roster.get("completed")
            or roster.get("failed")
            or handoffs
            or active_runs
            or int(item.get("review_ready_count") or 0)
            or int(item.get("pending_approvals_count") or 0)
        )
        if not has_reportable_evidence:
            continue
        reports.append(
            {
                "workspace_id": workspace_id,
                "display_name": str(item.get("display_name") or workspace_id),
                "health": str(item.get("health") or item.get("tone") or "nominal"),
                "active_runs": active_runs,
                "review_ready_count": int(item.get("review_ready_count") or 0),
                "pending_approvals_count": int(item.get("pending_approvals_count") or 0),
                "top_signal_title": str(item.get("top_signal_title") or "").strip(),
                "roster": roster,
                "handoffs": handoffs,
            }
        )
    reports.sort(
        key=lambda row: (
            {"critical": 0, "attention": 1, "nominal": 2}.get(str(row["health"]), 3),
            str(row["display_name"]).lower(),
        )
    )
    return reports


def fingerprint_rows(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "workspace_id": row["workspace_id"],
            "health": row["health"],
            "active_runs": row["active_runs"],
            "busy_employee_ids": [
                str(employee.get("employee_id") or employee.get("name") or "")
                for employee in row["roster"].get("busy", [])
            ],
            "handoff_receipt_ids": [
                str(handoff.get("receipt_id") or "") for handoff in row.get("handoffs", [])
            ],
        }
        for row in reports
    ]


def _name_role(row: dict[str, Any]) -> str:
    name = str(row.get("name") or "Teammate").strip()
    role = str(row.get("role_label") or row.get("role") or "").strip()
    return f"{name} ({role})" if role else name


def workspace_update_bits(reports: list[dict[str, Any]], spell_count: Callable[[int], str]) -> list[str]:
    bits: list[str] = []
    for report in reports:
        name = str(report.get("display_name") or report.get("workspace_id") or "Workspace")
        roster = report.get("roster") if isinstance(report.get("roster"), dict) else {}
        busy, completed, failed = (
            roster.get("busy") or [],
            roster.get("completed") or [],
            roster.get("failed") or [],
        )
        details: list[str] = []
        if busy:
            details.append("busy: " + ", ".join(_name_role(row) for row in busy[:4]))
        active_runs = int(report.get("active_runs") or 0)
        if active_runs and not busy:
            details.append(f"{spell_count(active_runs)} active run{'s' if active_runs != 1 else ''}")
        if completed:
            details.append(
                "last recorded completion: "
                + ", ".join(_name_role(row) for row in completed[:3])
            )
        if failed:
            details.append(
                "last recorded failure: "
                + ", ".join(_name_role(row) for row in failed[:3])
            )
        review_ready = int(report.get("review_ready_count") or 0)
        approvals = int(report.get("pending_approvals_count") or 0)
        if review_ready:
            details.append(f"{spell_count(review_ready)} ready for review")
        if approvals:
            details.append(f"{spell_count(approvals)} awaiting approval")
        signal = str(report.get("top_signal_title") or "").strip()
        if signal:
            details.append(f"signal: {_scrub_operator_line(signal, max_len=80)}")
        if details:
            bits.append(f"{name} — {'; '.join(details)}")
    return bits[:12]


def fleet_lead_rollup_bits(
    snapshot: dict[str, Any],
    reports: list[dict[str, Any]],
    rollup_builder: Callable[[dict[str, Any]], list[str]],
) -> list[str]:
    bits: list[str] = []
    for report in reports:
        # A fleet report must not attribute an inferred plan to a Lead. The
        # builder also has board-derived fallback prose, so call it only when
        # this workspace has a stored, verified Lead handoff receipt.
        if not report.get("handoffs"):
            continue
        workspace_name = str(report.get("display_name") or report.get("workspace_id") or "Workspace")
        nested = {
            **snapshot,
            "workspace_id": report.get("workspace_id"),
            "roster": report.get("roster") or {},
            "handoffs": report.get("handoffs") or [],
            "top_signals": (
                [{"title": report.get("top_signal_title"), "summary": ""}]
                if report.get("top_signal_title")
                else []
            ),
            "awaiting_engagement_count": 0,
        }
        bits.extend(f"{workspace_name} — {line}" for line in rollup_builder(nested)[:2])
    return bits[:12]


def render_report_text(
    *,
    snapshot: dict[str, Any],
    attention: list[str],
    work: list[str],
    workspace_updates: list[str],
    rollups: list[str],
    fleet: list[str],
    next_move: str,
    spell_count: Callable[[int], str],
) -> tuple[str, str]:
    fleet_data = snapshot.get("fleet") or {}
    checked = int(fleet_data.get("count") or fleet_data.get("workspace_count") or 0)
    parts = [
        "Fleet report",
        "Attention:\n- " + "\n- ".join(attention or ["Nothing screaming"]),
        f"Workspaces checked: {spell_count(checked)}.",
        "Workspace evidence:\n- "
        + "\n- ".join(workspace_updates or ["No current or recorded workspace work found"]),
        "Work in flight:\n- " + "\n- ".join(work or ["Idle"]),
        "Stored Lead evidence:\n- " + "\n- ".join(rollups)
        if rollups
        else "Stored Lead evidence: no verified receipt found.",
        "Fleet:\n- " + "\n- ".join(fleet),
        f"Next move:\n- {next_move}",
    ]
    text = "\n\n".join(parts)
    spoken = " ".join(
        [
            "Here's the fleet report.",
            f"Attention: {', '.join(attention) if attention else 'nothing screaming'}.",
            f"Workspace evidence: {', '.join(workspace_updates[:3]) if workspace_updates else 'none found'}.",
            f"Stored Lead evidence: {'; '.join(rollups[:3]) if rollups else 'no verified receipt found'}.",
            f"Fleet: {', '.join(fleet)}.",
            f"Next move: {next_move}.",
        ]
    )
    return text, spoken
