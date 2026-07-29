"""Build CLI runtime status records and choose the default target."""

from __future__ import annotations

import os
from typing import Any

from app.cli_runtime.auth_probes import vault_auth_overlay

StatusRecord = dict[str, Any]


def local_runtime_record(
    runtime_id: str,
    *,
    family: str,
    binary: str,
    auth: StatusRecord,
    label: str,
) -> StatusRecord:
    return {
        "id": runtime_id,
        "family": family,
        "label": label,
        "target_type": "local",
        "available": bool(binary),
        "binary": binary,
        "auth": auth,
        "ready": bool(binary) and bool(auth.get("logged_in")),
        "mode_support": ["ask", "plan", "agent", "debug"],
    }


def cloud_runtime_record(
    runtime_id: str,
    *,
    family: str,
    label: str,
    vault_posture: dict[str, Any],
    env_keys: dict[str, str],
) -> StatusRecord:
    enabled = str(
        os.environ.get(f"AXON_WATCH_{runtime_id.upper()}_ENABLED") or ""
    ).strip().lower() in {"1", "true", "yes", "on"}
    auth = vault_auth_overlay(
        runtime_id,
        vault_posture=vault_posture,
        env_keys=env_keys,
    ) or {
        "logged_in": False,
        "auth_method": "",
        "provider_label": label,
        "vault_posture": vault_posture.get("posture"),
        "message": (
            "Cloud runtime not configured yet in Axon-X."
            if not enabled
            else "Cloud runtime flagged as enabled."
        ),
    }
    if enabled and auth.get("logged_in"):
        auth = {
            **auth,
            "auth_method": "vault_api_key",
            "message": "Cloud runtime enabled with vault-fed credentials.",
        }
    ready = bool(enabled) and bool(auth.get("logged_in"))
    if enabled and not auth.get("logged_in") and vault_posture.get("unlocked"):
        auth = {
            **auth,
            "message": str(
                vault_posture.get("hint")
                or "Cloud runtime enabled but vault keys are missing for this target."
            ),
        }
    return {
        "id": runtime_id,
        "family": family,
        "label": label,
        "target_type": "cloud",
        "available": enabled,
        "binary": "",
        "auth": auth,
        "ready": ready,
        "mode_support": ["ask", "plan", "agent", "debug"],
    }


def choose_default_runtime(
    local: list[StatusRecord],
    cloud: list[StatusRecord],
) -> str:
    explicit = str(os.environ.get("AXON_WATCH_IDE_RUNTIME_TARGET", "")).strip().lower()
    known = {record["id"]: record for record in [*local, *cloud]}
    if explicit in known:
        return explicit

    preferred_family = str(
        os.environ.get("AXON_WATCH_IDE_RUNTIME_FAMILY", "cursor")
    ).strip().lower()
    family_order = [preferred_family, "cursor", "codex"]
    seen: set[str] = set()
    for family in family_order:
        if family in seen:
            continue
        seen.add(family)
        for record in local:
            if record["family"] == family and record["ready"]:
                return str(record["id"])
    for record in local:
        if record["available"]:
            return str(record["id"])
    return "cursor_local"
