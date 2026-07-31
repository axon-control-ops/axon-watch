"""Ownership guards for OTA / EAS / Expo ship commands on agent terminal jobs.

Client-ops Leads (e.g. Young Eagles / Imani) must not publish DashPro OTAs by
``cd`` into the product tree or by passing ``--workspace workspace_dashpro``.
Ship jobs belong to the product workspace that owns the project root.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.cli_runtime.long_running_shell import is_long_running_ship_shell

DASHPRO_WORKSPACE_ID = "workspace_dashpro"

_PRODUCTION_OTA_RE = re.compile(
    r"\bota:production\b|RELEASE_GUARD_ALLOW_PRODUCTION_OTA\s*=\s*1",
    re.IGNORECASE,
)
_FOREIGN_DASHPRO_ROOT_RE = re.compile(
    r"(?:^|[;'\"`\s]|&&|\|\||;)"
    r"(?:cd\s+|pushd\s+)?"
    r"[^\s;'\"`]*"
    r"(?:/product/dashpro|/Projectx/product/dashpro|product/dashpro)\b",
    re.IGNORECASE,
)


class ShipCommandGuardError(ValueError):
    """Ship command rejected for wrong workspace / foreign ownership."""


def is_production_ota_command(command: str) -> bool:
    return bool(_PRODUCTION_OTA_RE.search(str(command or "")))


def command_targets_dashpro_product_root(command: str) -> bool:
    text = str(command or "")
    if _FOREIGN_DASHPRO_ROOT_RE.search(text):
        return True
    return "product/dashpro" in text.lower()


def _binding_root(workspace_id: str) -> Path | None:
    try:
        from app.workspace_project_bindings import get_workspace_project_binding

        binding = get_workspace_project_binding(workspace_id)
    except Exception:  # noqa: BLE001 — guard must soft-fail closed on ship only
        return None
    if binding is None:
        return None
    return Path(binding.project_root)


def assert_ship_command_allowed(
    *,
    workspace_id: str,
    command: str,
    source_workspace_id: str | None = None,
) -> None:
    """Raise ShipCommandGuardError when a ship job is foreign to the caller.

    Rules:
    - OTA / ``eas update`` / Expo export ship verbs must enqueue on the owning
      product workspace (DashPro for DashPro roots).
    - ``source_workspace_id`` (agent home workspace) must match the owner when
      set — blocks YE Lead using ``--workspace workspace_dashpro``.
    - ``cd …/product/dashpro && ota`` from a non-DashPro enqueue is rejected.
    """
    clean_workspace = str(workspace_id or "").strip()
    clean_source = str(source_workspace_id or "").strip()
    text = str(command or "").strip()
    if not text or not clean_workspace:
        return

    ship = is_long_running_ship_shell(text)
    targets_dashpro = command_targets_dashpro_product_root(text)
    if not ship and not targets_dashpro:
        return

    owner = DASHPRO_WORKSPACE_ID
    if ship or targets_dashpro:
        if clean_workspace != owner:
            raise ShipCommandGuardError(
                "DashPro Expo/EAS OTA ship jobs must run from workspace_dashpro "
                "(Dana / DashPro board). This workspace cannot publish parent-app "
                "updates. Create a cross-workspace handoff: "
                f"POST /api/workspaces/{clean_workspace}/handoffs "
                f'{{"target_workspace_id":"{owner}","task":"<OTA goal>"}}.'
            )
        if clean_source and clean_source != owner:
            raise ShipCommandGuardError(
                f"Ship job rejected: caller workspace {clean_source} is not allowed "
                f"to publish on {owner}. App UI / parent dashboard / Expo OTA belong "
                "to DashPro (Dana). Hand off via POST …/handoffs — do not cd into "
                "the DashPro product tree from a client-ops Lead thread."
            )

    # Extra belt: if enqueue workspace root is not DashPro but command cds there.
    root = _binding_root(clean_workspace)
    if root is not None and ship:
        root_s = str(root).replace("\\", "/").lower()
        if "product/dashpro" in root_s and clean_workspace != owner:
            raise ShipCommandGuardError(
                f"Workspace {clean_workspace} is bound to a DashPro-like root but "
                f"id is not {owner}; refusing ship enqueue."
            )


__all__ = [
    "DASHPRO_WORKSPACE_ID",
    "ShipCommandGuardError",
    "assert_ship_command_allowed",
    "command_targets_dashpro_product_root",
    "is_production_ota_command",
]
