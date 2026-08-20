"""Authoritative fleet map of company Leads for Lead prompts.

Leads only see their own company roster by default. Cross-workspace ownership
(e.g. DashPro app UI vs Young Eagles centre ops) must be explicit so they hand
off instead of working in the wrong tree.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FLEET_LEADS_MARKER = (
    "Fleet leads map (authoritative — prefer handoffs over foreign work):"
)


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _project_kind(
    *,
    workspace_id: str,
    project_root: str | None,
    display_name: str,
    company_name: str = "",
) -> str:
    wid = workspace_id.strip().lower()
    root = (project_root or "").replace("\\", "/").lower()
    label = display_name.strip().lower()
    company = company_name.strip().lower()
    # Product company name is Axon-X; workspace id is workspace_axon_watch (no workspace_axon_x).
    if wid == "workspace_axon_watch" or company == "axon-x" or "axon-watch" in root:
        return "Axon console"
    if "/product/" in root or "product app" in label:
        return "product app"
    if "/client/" in root or "client ops" in label or "day care" in label:
        return "client ops"
    if "/internal/" in root:
        return "internal tool"
    if root:
        return Path(root).name or "project"
    return "workspace"


def _binding_metadata() -> dict[str, dict[str, str]]:
    """Read display_name + raw project_root without requiring roots to exist on disk.

    ``load_workspace_project_bindings`` resolves and validates roots; one missing
    path would wipe the whole map. Fleet prompts only need labels/path hints.
    """
    from app.workspace_project_bindings import default_bindings_file

    path = default_bindings_file()
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    entries = payload.get("bindings")
    if not isinstance(entries, dict):
        return {}
    out: dict[str, dict[str, str]] = {}
    for workspace_id, entry in entries.items():
        wid = str(workspace_id or "").strip()
        if not wid or not isinstance(entry, dict):
            continue
        display_name = str(entry.get("display_name") or "").strip()
        project_root = str(entry.get("project_root") or "").strip()
        out[wid] = {
            "display_name": display_name,
            "project_root": project_root,
        }
    return out


def format_fleet_leads_block(
    rows: list[dict[str, Any]],
) -> str:
    """Format pre-built fleet lead rows for prompt injection."""
    if not rows:
        return ""
    lines = [
        FLEET_LEADS_MARKER,
        "Each company Lead below owns that workspace's tree. Do not implement "
        "work that belongs in another company's project root.",
    ]
    for row in rows:
        name = _clean(row.get("lead_name")) or "Lead"
        workspace_id = _clean(row.get("workspace_id")) or "workspace"
        company = _clean(row.get("company_name")) or workspace_id
        owns = _clean(row.get("owns")) or "company priorities"
        kind = _clean(row.get("project_kind")) or "workspace"
        project_label = _clean(row.get("display_name")) or company
        lines.append(
            f"- {name} · {company} ({workspace_id}) [{kind}: {project_label}] "
            f"— owns: {owns}"
        )
    lines.extend(
        [
            "Routing rules:",
            "- App UI / parent dashboard / Expo / EAS Update (OTA) → DashPro "
            "(workspace_dashpro, Dana → Priya for UI); hand off via "
            "POST /api/workspaces/{source}/handoffs with target_workspace_id="
            "workspace_dashpro — do not patch the product app in a client-ops tree.",
            "- Centre ops / letters / graduation / enrolment data → Young Eagles "
            "(workspace_young_eagles_day_care, Imani).",
            "- Thapelosego supplier bids / RFQ packs / company documents → TPS "
            "(workspace_tps, Noor).",
            "- Axon console / Mission Control / Fast Gate → Axon-X "
            "(workspace_axon_watch, Mira).",
            "Cross-workspace coordination: Leads message each other by creating a "
            "handoff (POST /api/workspaces/{source}/handoffs). That posts to both "
            "Leads' IDE threads and opens a target-workspace task — prefer this over "
            "chatting across workspaces without a ticket.",
            "Prefer creating a cross-workspace handoff over doing foreign work in the wrong repo.",
            "EAS Update only ships JS/assets (not native binary changes); native/"
            "SDK/permission work still needs a new build in the DashPro app repo.",
        ]
    )
    return "\n".join(lines)


def collect_fleet_lead_rows() -> list[dict[str, Any]]:
    """Load Lead rows from workspace-agents.json + binding labels."""
    from app.workspace_agents.config_loader import load_workspace_agent_configs

    try:
        _configs, _defaults, companies, _staffing = load_workspace_agent_configs()
    except Exception:  # noqa: BLE001 — prompt helper must soft-fail
        return []

    bindings = _binding_metadata()

    rows: list[dict[str, Any]] = []
    for workspace_id, company in sorted(companies.items()):
        lead = None
        for employee in company.employees:
            if str(employee.role or "").strip().lower() != "lead":
                continue
            if employee.enabled is False:
                continue
            lead = employee
            break
        if lead is None:
            continue
        meta = bindings.get(workspace_id) or {}
        company_name = company.company_name or meta.get("display_name") or workspace_id
        display_name = meta.get("display_name") or company_name
        project_root = meta.get("project_root") or None
        rows.append(
            {
                "workspace_id": workspace_id,
                "company_name": company_name,
                "lead_name": lead.name or "Lead",
                "owns": lead.owns or "company priorities",
                "display_name": display_name,
                "project_root": project_root,
                "project_kind": _project_kind(
                    workspace_id=workspace_id,
                    project_root=project_root,
                    display_name=str(display_name),
                    company_name=str(company_name),
                ),
            }
        )
    return rows


def build_fleet_leads_context() -> str:
    """Authoritative fleet Lead map for Lead persona prompts."""
    return format_fleet_leads_block(collect_fleet_lead_rows())
