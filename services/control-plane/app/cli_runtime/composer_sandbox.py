"""Durable, lazily materialized per-workspace composer isolation."""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

from app.persistence import composer_sandbox_store
from app.safe_improvement.isolated_executor import (
    IsolationError,
    agent_workspace_for_isolation,
    cleanup_isolation_root,
    create_isolation_root,
)
from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root
from app.workspace_delivery.publish import list_isolation_changed_paths

_LOCK = threading.RLock()


class DirtySandboxError(RuntimeError):
    """A destructive disable would discard unpromoted changes."""


def _flag(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    return default if raw is None else raw.strip().lower() in {"1", "true", "yes", "on"}


def _auto_enabled() -> bool:
    if not _flag("AXON_SANDBOX_POLICY_V2", True):
        return False
    try:
        from app.persistence import operator_presence_settings_store

        settings = operator_presence_settings_store.load_settings()
        return str(settings.get("autonomy_mode") or "manual").strip().lower() == "full"
    except Exception:
        return False


def _env_forced() -> bool:
    return os.environ.get("AXON_COMPOSER_SANDBOX_FORCE", "").strip() == "1"


def _root(state: dict[str, Any]) -> Path | None:
    raw = str(state.get("checkout_root") or "").strip()
    return Path(raw).expanduser().resolve() if raw else None


def _root_valid(root: Path | None) -> bool:
    if root is None or not root.is_dir():
        return False
    try:
        agent_workspace_for_isolation(root)
    except IsolationError:
        return False
    return True


def _changed_paths(root: Path | None) -> list[str]:
    return list_isolation_changed_paths(root) if _root_valid(root) and root else []


def _materialize(workspace_id: str) -> Path:
    with _LOCK:
        state = composer_sandbox_store.get_state(workspace_id)
        existing = _root(state)
        if _root_valid(existing) and existing is not None:
            return existing
        checkout_id = composer_sandbox_store.allocate_checkout_id(workspace_id)
        root = create_isolation_root(
            proposal_id=checkout_id,
            bound_project_root=resolve_workspace_root(workspace_id),
        )
        composer_sandbox_store.save_state(
            workspace_id,
            checkout_id=checkout_id,
            checkout_root=str(root),
            retained_reason="",
        )
        return root


def _status(workspace_id: str, *, materialize: bool = False) -> dict[str, Any]:
    state = composer_sandbox_store.get_state(workspace_id)
    manual = bool(state.get("manual_enabled"))
    auto = _auto_enabled()
    forced = _env_forced()
    retained = bool(str(state.get("retained_reason") or "").strip())
    enabled = forced or auto or manual or retained
    if enabled and materialize:
        _materialize(workspace_id)
        state = composer_sandbox_store.get_state(workspace_id)
    root = _root(state)
    materialized = _root_valid(root)
    dirty = bool(_changed_paths(root))
    source = (
        "env" if forced else "auto+manual" if auto and manual else "auto" if auto
        else "manual" if manual else "retained" if retained else "off"
    )
    lifecycle = (
        "retained-dirty" if retained else "active" if materialized
        else "auto-ready" if enabled else "off"
    )
    return {
        "enabled": enabled,
        "session_enabled": manual,
        "env_forced": forced,
        "source": source,
        "manual_enabled": manual,
        "auto_enabled": auto,
        "materialized": materialized,
        "dirty": dirty,
        "effective_access": "full" if enabled else "operator",
        "retained_reason": str(state.get("retained_reason") or ""),
        "can_disable": not forced and not auto and not dirty,
        "checkout_id": state.get("checkout_id"),
        "lifecycle": lifecycle,
    }


def sandbox_status(workspace_id: str) -> dict[str, Any]:
    return _status(str(workspace_id or "").strip())


def enable_sandbox(workspace_id: str) -> dict[str, Any]:
    cleaned = str(workspace_id or "").strip()
    composer_sandbox_store.save_state(cleaned, manual_enabled=True, retained_reason="")
    _materialize(cleaned)
    return _status(cleaned)


def disable_sandbox(workspace_id: str) -> dict[str, Any]:
    cleaned = str(workspace_id or "").strip()
    with _LOCK:
        state = composer_sandbox_store.get_state(cleaned)
        root = _root(state)
        if _changed_paths(root):
            composer_sandbox_store.save_state(
                cleaned, manual_enabled=False, retained_reason="unpromoted changes"
            )
            raise DirtySandboxError("Sandbox contains unpromoted changes; publish or discard it")
        composer_sandbox_store.save_state(cleaned, manual_enabled=False)
        if not _auto_enabled() and root is not None:
            cleanup_isolation_root(root)
            composer_sandbox_store.save_state(
                cleaned, checkout_id=None, checkout_root=None, retained_reason=""
            )
    return _status(cleaned)


def discard_sandbox(workspace_id: str) -> dict[str, Any]:
    cleaned = str(workspace_id or "").strip()
    with _LOCK:
        state = composer_sandbox_store.get_state(cleaned)
        root = _root(state)
        if root is not None:
            cleanup_isolation_root(root)
        composer_sandbox_store.save_state(
            cleaned,
            manual_enabled=False,
            checkout_id=None,
            checkout_root=None,
            retained_reason="",
        )
    return _status(cleaned)


def review_sandbox(workspace_id: str) -> dict[str, Any]:
    cleaned = str(workspace_id or "").strip()
    root = _root(composer_sandbox_store.get_state(cleaned))
    return {**_status(cleaned), "changed_paths": _changed_paths(root)}


def publish_sandbox(workspace_id: str) -> dict[str, Any]:
    """Publish a reviewed composer checkout through the normal delivery gate."""
    cleaned = str(workspace_id or "").strip()
    state = composer_sandbox_store.get_state(cleaned)
    root = _root(state)
    changed = _changed_paths(root)
    if root is None or not changed:
        return {**_status(cleaned), "published": False, "detail": "no changes"}
    from app.runs.service import complete_run, create_run, fail_run
    from app.workspace_delivery import get_workspace_delivery_policy, publish_worker_isolation

    if get_workspace_delivery_policy(cleaned) is None:
        raise IsolationError("workspace delivery is not configured; refusing to discard changes")
    run = create_run(
        workspace_id=cleaned,
        mode="agent",
        summary="Publish reviewed composer Sandbox changes",
        detail="Operator-approved composer Sandbox delivery",
    )
    run_id = str(run["run_id"])
    result = publish_worker_isolation(
        workspace_id=cleaned,
        run_id=run_id,
        isolation_root=root,
        turn_subject="Publish reviewed composer Sandbox changes",
    )
    if not result.ok:
        fail_run(run_id, receipt_summary=result.detail, actor="composer_sandbox")
        return {
            **_status(cleaned), "published": False, "run_id": run_id,
            "stage": result.stage, "detail": result.detail,
        }
    complete_run(run_id)
    if result.cleanup_isolation:
        cleanup_isolation_root(root)
        composer_sandbox_store.save_state(
            cleaned, checkout_id=None, checkout_root=None, retained_reason=""
        )
    return {
        **_status(cleaned), "published": True, "run_id": run_id,
        "stage": result.stage, "detail": result.detail,
        "delivery": result.delivery,
    }


def resolve_sandbox_workspace_root(workspace_id: str) -> Path | None:
    cleaned = str(workspace_id or "").strip()
    if not _status(cleaned)["enabled"]:
        return None
    return agent_workspace_for_isolation(_materialize(cleaned))


def resolve_sandbox_execution(
    workspace_id: str, composer_mode: str, stored_access: str
) -> tuple[Path | None, str]:
    root = resolve_sandbox_workspace_root(workspace_id)
    from app.cli_runtime.approval_gate import is_tool_capable_composer_mode

    access = "full" if root is not None and is_tool_capable_composer_mode(composer_mode) else stored_access
    return root, access


def reconcile_autonomy_transition(previous_mode: str, next_mode: str) -> None:
    """Drop only clean Auto-owned sessions when Full Auto is switched off."""
    if previous_mode != "full" or next_mode == "full":
        return
    with _LOCK:
        for state in composer_sandbox_store.list_states():
            if state.get("manual_enabled"):
                continue
            workspace_id = str(state.get("workspace_id") or "")
            root = _root(state)
            if _changed_paths(root):
                composer_sandbox_store.save_state(
                    workspace_id, retained_reason="Full Auto ended with unpromoted changes"
                )
                continue
            if root is not None:
                cleanup_isolation_root(root)
            composer_sandbox_store.save_state(
                workspace_id, checkout_id=None, checkout_root=None, retained_reason=""
            )


def reconcile_persisted_sandboxes() -> None:
    """Recover durable sessions and remove only proven-clean Auto-only leftovers."""
    with _LOCK:
        auto = _auto_enabled()
        for state in composer_sandbox_store.list_states():
            workspace_id = str(state.get("workspace_id") or "")
            root = _root(state)
            if root is not None and not _root_valid(root):
                composer_sandbox_store.save_state(
                    workspace_id,
                    checkout_id=None,
                    checkout_root=None,
                    retained_reason=(
                        "retained checkout missing; operator review required"
                        if state.get("retained_reason") else ""
                    ),
                )
                continue
            if state.get("manual_enabled") or auto or root is None:
                continue
            if _changed_paths(root):
                composer_sandbox_store.save_state(
                    workspace_id, retained_reason="Recovered unpromoted Sandbox changes"
                )
            else:
                cleanup_isolation_root(root)
                composer_sandbox_store.save_state(
                    workspace_id, checkout_id=None, checkout_root=None, retained_reason=""
                )


__all__ = [
    "DirtySandboxError", "IsolationError", "WorkspaceRootError", "disable_sandbox",
    "discard_sandbox", "enable_sandbox", "publish_sandbox",
    "reconcile_autonomy_transition", "reconcile_persisted_sandboxes",
    "resolve_sandbox_execution", "resolve_sandbox_workspace_root",
    "review_sandbox", "sandbox_status",
]
