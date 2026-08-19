"""Durable, lazily materialized per-workspace composer isolation."""

from __future__ import annotations

import json
import os
import subprocess
import threading
from pathlib import Path
from typing import Any

from app.persistence import composer_sandbox_store
from app.safe_improvement.isolated_executor import (
    IsolationError,
    agent_workspace_for_isolation,
    cleanup_isolation_root,
    create_isolation_root,
    read_baseline_metadata,
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
    # Borrowed toolchain links are filtered inside list_changed_paths itself, so
    # delivery, the verifier contract and this review all agree on one answer.
    return list_isolation_changed_paths(root) if _root_valid(root) and root else []


def _workspace_root(workspace_id: str) -> Path | None:
    try:
        return resolve_workspace_root(workspace_id)
    except WorkspaceRootError:
        return None


def _workspace_changed_paths(root: Path | None) -> list[str]:
    if root is None or not root.is_dir():
        return []
    try:
        return list_isolation_changed_paths(root)
    except Exception:
        return []


def _branch_name(root: Path | None) -> str:
    if root is None or not root.is_dir():
        return ""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (result.stdout or "").strip() if result.returncode == 0 else ""


def _baseline(root: Path | None) -> dict[str, Any]:
    if not _root_valid(root) or root is None:
        return {}
    try:
        return read_baseline_metadata(root)
    except (IsolationError, OSError, ValueError):
        return {}


def _file_diffs(root: Path | None, paths: list[str]) -> list[dict[str, Any]]:
    """Unified diff per changed path, so Review can show the actual change.

    Review previously returned only path names, which is why the button read as
    doing nothing: there was nothing for the UI to open. ``--no-index`` against
    /dev/null covers files that are new in the checkout and therefore absent
    from HEAD.
    """
    if not _root_valid(root) or root is None:
        return []
    diffs: list[dict[str, Any]] = []
    for path in paths[:50]:  # A review surface, not a bulk export.
        text = ""
        for args in (
            ["git", "diff", "--unified=3", "HEAD", "--", path],
            ["git", "diff", "--no-index", "--unified=3", "--", "/dev/null", path],
        ):
            try:
                result = subprocess.run(
                    args, cwd=str(root), capture_output=True, text=True, timeout=15, check=False
                )
            except (OSError, subprocess.TimeoutExpired):
                continue
            text = (result.stdout or "").strip()
            if text:
                break
        added = sum(
            1 for line in text.splitlines() if line.startswith("+") and not line.startswith("+++")
        )
        removed = sum(
            1 for line in text.splitlines() if line.startswith("-") and not line.startswith("---")
        )
        diffs.append({"path": path, "diff": text, "added": added, "removed": removed})
    return diffs


def _preview_contract(
    *,
    workspace_id: str,
    sandbox_root: Path | None,
    bound_root: Path | None,
) -> dict[str, Any]:
    if not _root_valid(sandbox_root) or sandbox_root is None:
        return {
            "available": False,
            "detail": "Sandbox checkout is not materialized yet.",
            "sandbox_url_hint": "",
        }
    # Imported lazily: the preview lane imports this module back for checkout
    # resolution.
    from app.cli_runtime.sandbox_preview import sandbox_preview_status

    live = sandbox_preview_status(workspace_id)
    running = bool(live.get("running"))
    example = _preview_example(sandbox_root)
    return {
        "available": True,
        "detail": (
            f"Sandbox preview is running at {live.get('url')} — it serves the "
            "checkout, so it shows Sandbox-only changes that the bound/root "
            "workspace preview does not."
            if running
            else "Start a Sandbox preview to see these changes running before publishing. "
            "The bound/root workspace preview does not show Sandbox-only changes."
        ),
        "checkout_root": str(sandbox_root),
        "bound_project_root": str(bound_root) if bound_root is not None else "",
        "running": running,
        "url": str(live.get("url") or ""),
        "port": live.get("port"),
        "job_id": str(live.get("job_id") or ""),
        "sandbox_url_hint": "Use a non-root preview port such as 8083 or 8084.",
        "root_url_hint": "localhost:8082 is expected to be the bound/root workspace unless explicitly relaunched from checkout_root.",
        "example": example,
        "workspace_id": workspace_id,
    }


def _preview_example(root: Path) -> str:
    """The command the Run preview button would issue, for copy-paste parity.

    Delegates to the preview lane so the displayed hint and the command that
    actually runs can never drift apart.
    """
    from app.cli_runtime.sandbox_preview import (
        PREVIEW_PORT_RANGE,
        SandboxPreviewError,
        sandbox_preview_command,
    )

    port = PREVIEW_PORT_RANGE.start
    try:
        return f"cd {root} && {sandbox_preview_command(root, port)}"
    except SandboxPreviewError:
        return f"cd {root} && run the workspace preview command on a spare port such as {port}"


def _ensure_checkout_runnable(checkout: Path) -> None:
    from app.cli_runtime.sandbox_preview import (
        SandboxPreviewError,
        ensure_isolation_checkout_runnable,
    )

    borrow = ensure_isolation_checkout_runnable(checkout)
    if borrow.get("ok"):
        return
    errors = borrow.get("errors") or []
    detail = "; ".join(str(item) for item in errors if str(item).strip())
    raise SandboxPreviewError(
        "sandbox checkout toolchain borrow failed"
        + (f": {detail}" if detail else "")
    )


def _materialize(workspace_id: str) -> Path:
    with _LOCK:
        state = composer_sandbox_store.get_state(workspace_id)
        existing = _root(state)
        if _root_valid(existing) and existing is not None:
            _ensure_checkout_runnable(existing)
            return existing
        checkout_id = composer_sandbox_store.allocate_checkout_id(workspace_id)
        root = create_isolation_root(
            proposal_id=checkout_id,
            bound_project_root=resolve_workspace_root(workspace_id),
        )
        _ensure_checkout_runnable(root)
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
    bound_root = _workspace_root(workspace_id)
    materialized = _root_valid(root)
    dirty = bool(_changed_paths(root))
    root_changed_paths = _workspace_changed_paths(bound_root)
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
        "checkout_root": str(root) if materialized and root is not None else "",
        "checkout_id": state.get("checkout_id"),
        "bound_project_root": str(bound_root) if bound_root is not None else "",
        "bound_branch": _branch_name(bound_root),
        "root_dirty": bool(root_changed_paths),
        "root_changed_paths": root_changed_paths[:40],
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
        composer_sandbox_store.save_state(
            cleaned, manual_enabled=False, retained_reason=""
        )
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
    bound_root = _workspace_root(cleaned)
    changed_paths = _changed_paths(root)
    return {
        **_status(cleaned),
        "changed_paths": changed_paths,
        "file_diffs": _file_diffs(root, changed_paths),
        "baseline": _baseline(root),
        "preview": _preview_contract(
            workspace_id=cleaned,
            sandbox_root=root,
            bound_root=bound_root,
        ),
    }


def publish_sandbox(workspace_id: str) -> dict[str, Any]:
    """Publish a reviewed composer checkout through the normal delivery gate."""
    cleaned = str(workspace_id or "").strip()
    state = composer_sandbox_store.get_state(cleaned)
    root = _root(state)
    changed = _changed_paths(root)
    if root is None or not changed:
        return {**_status(cleaned), "published": False, "detail": "no changes"}
    bound_root = _workspace_root(cleaned)
    root_changed = _workspace_changed_paths(bound_root)
    if root_changed:
        raise DirtySandboxError(
            "Bound workspace root has uncommitted changes; clean, stash, or commit root "
            "before publishing Sandbox changes"
        )
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
