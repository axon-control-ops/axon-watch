"""Disposable proposal sandbox (never mutates bound workspace root)."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

_SIDECAR_DIR = ".axon-si"
_BASELINE_FILE = "baseline.json"
_MARKER_FILE = "MARKER"
_METRICS_FILE = "metrics.json"


class IsolationError(RuntimeError):
    """Raised when a disposable sandbox root cannot be created safely."""


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sidecar(root: Path) -> Path:
    return root / _SIDECAR_DIR


def _run_git(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd is not None else None,
        check=False,
        capture_output=True,
        text=True,
    )


def _resolve_baseline_commit(bound_project_root: Path) -> str:
    result = _run_git(["rev-parse", "HEAD"], cwd=bound_project_root)
    if result.returncode != 0:
        raise IsolationError(
            f"bound project is not a git repository or has no HEAD: {bound_project_root}"
        )
    commit = (result.stdout or "").strip()
    if not commit:
        raise IsolationError(f"unable to resolve baseline commit for {bound_project_root}")
    return commit


def _write_sidecar_baseline(
    root: Path,
    *,
    proposal_id: str,
    bound_project_root: Path,
    baseline_commit: str,
    isolation_kind: str,
) -> None:
    sidecar = _sidecar(root)
    sidecar.mkdir(parents=True, exist_ok=True)
    (sidecar / _MARKER_FILE).write_text("baseline\n", encoding="utf-8")
    (sidecar / _METRICS_FILE).write_text(
        json.dumps({"latency_ms": 100.0}, sort_keys=True),
        encoding="utf-8",
    )
    (sidecar / _BASELINE_FILE).write_text(
        json.dumps(
            {
                "proposal_id": proposal_id,
                "bound_project_root": str(bound_project_root.resolve()),
                "baseline_commit": baseline_commit,
                "isolation_kind": isolation_kind,
                "isolation_root": str(root.resolve()),
                "created_at": _now(),
            },
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _try_worktree(bound_project_root: Path, checkout: Path, commit: str) -> bool:
    result = _run_git(
        ["worktree", "add", "--detach", str(checkout), commit],
        cwd=bound_project_root,
    )
    return result.returncode == 0 and checkout.is_dir()


def _try_shallow_clone(bound_project_root: Path, checkout: Path, commit: str) -> bool:
    if checkout.exists():
        shutil.rmtree(checkout, ignore_errors=True)
    clone = _run_git(
        [
            "clone",
            "--no-hardlinks",
            "--quiet",
            str(bound_project_root.resolve()),
            str(checkout),
        ]
    )
    if clone.returncode != 0 or not checkout.is_dir():
        return False
    pinned = _run_git(["checkout", "--detach", "--quiet", commit], cwd=checkout)
    if pinned.returncode != 0:
        shutil.rmtree(checkout, ignore_errors=True)
        return False
    return True


def create_isolation_root(*, proposal_id: str, bound_project_root: Path) -> Path:
    """
    Create a disposable git checkout for proposal work.

    Prefer a detached worktree at the bound project's HEAD commit; fall back to a
    local clone pinned to the same commit. Never writes into ``bound_project_root``.
    Fail closed if neither strategy succeeds.
    """
    bound = bound_project_root.expanduser().resolve()
    if not bound.is_dir():
        raise IsolationError(f"bound project root is not a directory: {bound}")

    baseline_commit = _resolve_baseline_commit(bound)
    parent = Path(tempfile.mkdtemp(prefix=f"axon-si-{proposal_id[:12]}-"))
    checkout = parent / "checkout"

    isolation_kind: str | None = None
    if _try_worktree(bound, checkout, baseline_commit):
        isolation_kind = "worktree"
    elif _try_shallow_clone(bound, checkout, baseline_commit):
        isolation_kind = "shallow_clone"
    else:
        shutil.rmtree(parent, ignore_errors=True)
        raise IsolationError(
            "failed to create disposable isolation root via worktree or clone; "
            "refusing to write the bound project root"
        )

    _write_sidecar_baseline(
        checkout,
        proposal_id=proposal_id,
        bound_project_root=bound,
        baseline_commit=baseline_commit,
        isolation_kind=isolation_kind,
    )
    return checkout


def read_baseline_metadata(root: Path) -> dict[str, Any]:
    path = _sidecar(root) / _BASELINE_FILE
    if not path.is_file():
        raise IsolationError(f"missing sandbox baseline metadata under {root}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_marker(root: Path) -> str:
    return (_sidecar(root) / _MARKER_FILE).read_text(encoding="utf-8").strip()


def read_metric(root: Path, metric: str) -> float:
    payload = json.loads((_sidecar(root) / _METRICS_FILE).read_text(encoding="utf-8"))
    if metric not in payload:
        raise KeyError(f"metric `{metric}` missing in isolation root")
    return float(payload[metric])


def apply_candidate_change(
    root: Path,
    *,
    metric: str,
    candidate_value: float,
    marker: str = "candidate",
) -> dict[str, Any]:
    """Mutate only the isolated sandbox sidecar; returns a change receipt."""
    metrics_path = _sidecar(root) / _METRICS_FILE
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    before = float(payload.get(metric, 0.0))
    payload[metric] = float(candidate_value)
    metrics_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    (_sidecar(root) / _MARKER_FILE).write_text(f"{marker}\n", encoding="utf-8")
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    meta = read_baseline_metadata(root)
    return {
        "receipt_id": f"iso_{uuid4().hex[:12]}",
        "kind": "isolated_candidate_change",
        "metric": metric,
        "before": before,
        "after": float(candidate_value),
        "marker": marker,
        "content_hash": f"sha256:{digest[:16]}",
        "isolation_root": str(root),
        "baseline_commit": meta.get("baseline_commit"),
        "isolation_kind": meta.get("isolation_kind"),
    }


def restore_baseline(
    root: Path,
    *,
    baseline_marker: str,
    baseline_metric_value: float,
    metric: str,
) -> dict[str, Any]:
    metrics_path = _sidecar(root) / _METRICS_FILE
    payload = {metric: float(baseline_metric_value)}
    metrics_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    (_sidecar(root) / _MARKER_FILE).write_text(f"{baseline_marker}\n", encoding="utf-8")
    return {
        "receipt_id": f"rb_{uuid4().hex[:12]}",
        "kind": "rollback",
        "metric": metric,
        "restored_value": float(baseline_metric_value),
        "restored_marker": baseline_marker,
        "isolation_root": str(root),
    }


def cleanup_isolation_root(root: Path) -> dict[str, Any]:
    """Remove the disposable checkout (worktree or clone) and its temp parent."""
    root = root.resolve()
    parent = root.parent
    meta: dict[str, Any] = {}
    try:
        meta = read_baseline_metadata(root)
    except IsolationError:
        meta = {}

    isolation_kind = str(meta.get("isolation_kind") or "")
    bound = str(meta.get("bound_project_root") or "")
    if isolation_kind == "worktree" and bound:
        _run_git(["worktree", "remove", "--force", str(root)], cwd=Path(bound))
        _run_git(["worktree", "prune"], cwd=Path(bound))

    removed = root.exists() or parent.exists()
    if parent.exists() and parent.name.startswith("axon-si-"):
        shutil.rmtree(parent, ignore_errors=True)
    elif root.exists():
        shutil.rmtree(root, ignore_errors=True)

    return {
        "receipt_id": f"cln_{uuid4().hex[:12]}",
        "kind": "isolation_cleanup",
        "isolation_root": str(root),
        "isolation_kind": isolation_kind or None,
        "baseline_commit": meta.get("baseline_commit"),
        "removed": bool(removed),
        "cleaned": not root.exists(),
    }


def agent_workspace_for_isolation(isolation_root: Path | str | None) -> Path:
    """
    Return the cwd/workspace agents and test commands must use during evaluation.

    Callers must not resolve paths back to the live bound project root.
    """
    if isolation_root is None or not str(isolation_root).strip():
        raise IsolationError("proposal has no disposable isolation root for agent work")
    root = Path(isolation_root).expanduser().resolve()
    if not root.is_dir():
        raise IsolationError(f"isolation root is missing or not a directory: {root}")
    meta = read_baseline_metadata(root)
    bound = Path(str(meta.get("bound_project_root") or "")).expanduser().resolve()
    if bound.exists() and root == bound:
        raise IsolationError("refusing to use bound project root as agent workspace")
    return root


def promote_candidate_marker(root: Path, *, marker: str) -> Path:
    promoted = _sidecar(root) / "PROMOTED"
    promoted.write_text(f"{marker}\n", encoding="utf-8")
    return promoted
