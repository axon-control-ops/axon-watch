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
# Runtime rewrites (research MCP, isolation markers) must not fail Gate 6 scope.
_RUNTIME_NOISE_PREFIXES = (".cursor/", ".axon-si/")
_CODE_CHECK_PREFIXES = (
    "apps/",
    "services/",
    "packages/",
    "scripts/",
    "tests/",
    "config/",
    ".github/",
)


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


def _normalize_rel_path(path: str) -> str:
    """Strip a single leading ``./`` only (do not use str.lstrip — it eats ``.cursor``)."""
    rel = str(path or "").strip()
    while rel.startswith("./"):
        rel = rel[2:]
    return rel


def is_runtime_noise_path(path: str) -> bool:
    """True for Cursor/isolation metadata the runtime rewrites during dispatch."""
    rel = _normalize_rel_path(path)
    if not rel:
        return False
    return any(
        rel == prefix.rstrip("/") or rel.startswith(prefix)
        for prefix in _RUNTIME_NOISE_PREFIXES
    )


def filter_runtime_noise_paths(paths: list[str] | None) -> list[str]:
    """Drop runtime metadata paths from a dirty set used for Gate 6 policy/checks."""
    if not paths:
        return []
    return [str(p) for p in paths if not is_runtime_noise_path(str(p))]


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
        if cleaned and not is_runtime_noise_path(cleaned):
            paths.append(cleaned)
    return paths


def code_paths_touched(changed_paths: list[str] | None) -> bool:
    """True when the dirty set includes paths that need lint/test/security checks."""
    if not changed_paths:
        return False
    for raw in changed_paths:
        rel = _normalize_rel_path(str(raw or ""))
        if not rel or is_runtime_noise_path(rel):
            continue
        for prefix in _CODE_CHECK_PREFIXES:
            if rel == prefix.rstrip("/") or rel.startswith(prefix):
                return True
        # Repo-root contract files are code-adjacent for Gate 6.
        if rel in {"project.axon.yaml", "package.json", "package-lock.json"}:
            return True
    return False


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
_CODE_HEAVY_CHECKS = frozenset({"lint", "test", "security", "diff_budget"})
_CONSOLE_WEB_PREFIX = "apps/console-web/"


def console_web_paths_touched(changed_paths: list[str] | None) -> bool:
    """True when the dirty set includes console-web sources that need vue-tsc/build."""
    if not changed_paths:
        return False
    for raw in changed_paths:
        rel = _normalize_rel_path(str(raw or ""))
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
    dirty set.

    When ``changed_paths`` is provided and has no code prefixes (after filtering
    runtime noise like ``.cursor/``), skip lint/test/security/diff_budget too —
    investigate-only or metadata-only shifts must not burn the full unit suite.
    """
    root = Path(workspace_root)
    base_timeout = timeout_seconds if timeout_seconds is not None else check_timeout_seconds()
    effective_paths = (
        filter_runtime_noise_paths(list(changed_paths))
        if changed_paths is not None
        else None
    )
    skip_frontend_heavy = effective_paths is not None and not console_web_paths_touched(
        effective_paths
    )
    skip_code_heavy = effective_paths is not None and not code_paths_touched(
        effective_paths
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
        if skip_code_heavy and name in _CODE_HEAVY_CHECKS:
            results[name] = {
                "passed": True,
                "output_excerpt": (
                    "skipped: no code-path changes in dirty set "
                    f"(prefixes={','.join(p.rstrip('/') for p in _CODE_CHECK_PREFIXES)})"
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
