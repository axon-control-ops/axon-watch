"""Execute Gate 6 verifier checks inside a workspace / isolation root."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from app.workspace_agents.verifier_checks import build_check_plan

_DEFAULT_CHECK_TIMEOUT_SECONDS = 90.0
# Full `./scripts/verify/run_contract_unit_tests.sh` exceeds the default 90s on
# this host; Python-only isolations still need a real pass, not a timeout fail.
_PYTHON_SUITE_TIMEOUT_SECONDS = 300.0
_MAX_SECRET_SCAN_BYTES = 200_000
_DEFAULT_FORBIDDEN = ("**/.env", "**/secrets/**", "**/*.pem")


def check_timeout_seconds() -> float:
    raw = os.environ.get("AXON_WATCH_GATE6_CHECK_TIMEOUT_SECONDS", "").strip()
    if not raw:
        return _DEFAULT_CHECK_TIMEOUT_SECONDS
    try:
        return max(5.0, min(float(raw), 600.0))
    except ValueError:
        return _DEFAULT_CHECK_TIMEOUT_SECONDS


def check_timeout_seconds_for(name: str, *, base: float | None = None) -> float:
    """Per-check timeout; the contract unit suite needs more than the default."""
    timeout = base if base is not None else check_timeout_seconds()
    if name == "test":
        return max(timeout, _PYTHON_SUITE_TIMEOUT_SECONDS)
    return timeout


def list_changed_paths(workspace_root: Path) -> list[str]:
    """Return tracked+untracked changed paths relative to the workspace root."""
    root = Path(workspace_root)
    if not root.is_dir():
        return []
    try:
        completed = subprocess.run(
            ["git", "status", "--porcelain", "-uall"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if completed.returncode != 0:
        return []
    paths: list[str] = []
    for line in completed.stdout.splitlines():
        if len(line) < 4:
            continue
        # status is first two chars; path starts at index 3 (may be rename "a -> b")
        rest = line[3:].strip()
        if " -> " in rest:
            rest = rest.split(" -> ", 1)[1].strip()
        cleaned = rest.strip().strip('"')
        if cleaned:
            paths.append(cleaned)
    return paths


def read_path_texts(
    workspace_root: Path,
    changed_paths: list[str],
    *,
    limit: int = 40,
) -> dict[str, str]:
    root = Path(workspace_root)
    texts: dict[str, str] = {}
    for rel in changed_paths[:limit]:
        candidate = root / rel
        if not candidate.is_file():
            continue
        try:
            if candidate.stat().st_size > _MAX_SECRET_SCAN_BYTES:
                continue
            texts[rel] = candidate.read_text(encoding="utf-8", errors="replace")[
                :_MAX_SECRET_SCAN_BYTES
            ]
        except OSError:
            continue
    return texts


_FRONTEND_HEAVY_CHECKS = frozenset({"typecheck", "build"})
_CONSOLE_WEB_PREFIX = "apps/console-web/"


def console_web_paths_touched(changed_paths: list[str] | None) -> bool:
    """True when the dirty set includes console-web sources that need vue-tsc/build."""
    if not changed_paths:
        return False
    for raw in changed_paths:
        rel = str(raw or "").lstrip("./")
        if rel == "apps/console-web" or rel.startswith(_CONSOLE_WEB_PREFIX):
            return True
    return False


def execute_check_plan(
    workspace_root: Path,
    contract: dict[str, Any],
    *,
    timeout_seconds: float | None = None,
    changed_paths: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Run required verifier commands; return results keyed by check name.

    When ``changed_paths`` is provided and does not touch ``apps/console-web/``,
    skip ``typecheck`` / ``build`` (vue-tsc / Vite). Those heaps OOM disposable
    worker isolations on Python-only control-plane fixes and do not validate the
    dirty set. Lint/test/security/diff_budget still run.
    """
    root = Path(workspace_root)
    base_timeout = timeout_seconds if timeout_seconds is not None else check_timeout_seconds()
    skip_frontend_heavy = changed_paths is not None and not console_web_paths_touched(
        changed_paths
    )
    results: dict[str, dict[str, Any]] = {}
    for item in build_check_plan(contract):
        name = str(item.get("name") or "").strip() or "check"
        command = str(item.get("command") or "").strip()
        timeout = check_timeout_seconds_for(name, base=base_timeout)
        if skip_frontend_heavy and name in _FRONTEND_HEAVY_CHECKS:
            results[name] = {
                "passed": True,
                "output_excerpt": (
                    f"skipped: no {_CONSOLE_WEB_PREFIX.rstrip('/')} changes in dirty set"
                ),
            }
            continue
        if not command or command.startswith("<missing command:"):
            results[name] = {
                "passed": False,
                "output_excerpt": f"missing command for check '{name}'",
            }
            continue
        if not root.is_dir():
            results[name] = {
                "passed": False,
                "output_excerpt": f"workspace root missing: {root}",
            }
            continue
        try:
            completed = subprocess.run(
                command,
                cwd=str(root),
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            excerpt = (completed.stdout or "") + (completed.stderr or "")
            results[name] = {
                "passed": completed.returncode == 0,
                "output_excerpt": excerpt.strip()[:2000] or f"exit={completed.returncode}",
            }
        except subprocess.TimeoutExpired:
            results[name] = {
                "passed": False,
                "output_excerpt": f"timed out after {timeout:.0f}s: {command}",
            }
        except OSError as exc:
            results[name] = {
                "passed": False,
                "output_excerpt": f"failed to start: {exc}",
            }
    return results


def inspect_fallback_contract() -> dict[str, Any]:
    """When a workspace has no project.axon.yaml, still apply secret/path policy."""
    return {
        "project_id": "inspect_fallback",
        "certification_level": "inspect_only",
        "inspect_only": True,
        "adapters": [],
        "unsupported_adapters": [],
        "commands": {},
        "allowed_paths": [],
        "forbidden_path_globs": list(_DEFAULT_FORBIDDEN),
        "verifier": {
            "identity": "verifier",
            "immutable_to_implementer": True,
            "required_checks": [],
        },
    }
