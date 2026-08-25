"""Canonical platform doctor. Every WARN/FAIL includes a next action."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Callable

from app.auth.settings import auth_mode, is_remotely_reachable, operator_token
from app.platform_recovery.autonomy import autonomy_label, configured_autonomy_level
from app.platform_recovery.circuit_breaker import list_circuits
from app.platform_recovery.process_inventory import inspect_processes
from app.platform_recovery.projection import build_recovery_center

HttpProbe = Callable[[str], tuple[int, str]]


def _status(ok: bool, *, warn: bool = False, blocked: bool = False) -> str:
    if blocked:
        return "BLOCKED"
    if ok:
        return "WARN" if warn else "PASS"
    return "FAIL"


def _check(name: str, status: str, next_action: str, detail: str = "") -> dict[str, Any]:
    return {"name": name, "status": status, "next_action": next_action, "detail": detail}


def run_doctor(
    *,
    repo_root: str | None = None,
    http_probe: HttpProbe | None = None,
) -> dict[str, Any]:
    root = Path(repo_root or Path(__file__).resolve().parents[4])
    checks: list[dict[str, Any]] = []

    db = os.environ.get("AXON_WATCH_CONTROL_PLANE_DB", "").strip()
    db_ok = bool(db and Path(db).exists()) or not db
    checks.append(
        _check(
            "database",
            _status(db_ok, warn=not db),
            "Set AXON_WATCH_CONTROL_PLANE_DB inside the repo .local/state tree."
            if not db_ok
            else "Database path is configured.",
            db or "unset (in-memory/test)",
        )
    )

    mode = auth_mode()
    remote = is_remotely_reachable()
    token = operator_token()
    auth_ok = not remote or bool(token)
    checks.append(
        _check(
            "authentication",
            _status(auth_ok, warn=mode == "off" and not remote),
            "Set AXON_WATCH_OPERATOR_TOKEN before exposing this host."
            if not auth_ok
            else f"auth_mode={mode} remote={remote}",
        )
    )

    recovery = build_recovery_center(persist=False)
    stale = int(recovery.get("attention_count") or 0)
    checks.append(
        _check(
            "stale_runs",
            _status(True, warn=stale > 0),
            "Open Recovery Center and reconcile stale items."
            if stale
            else "No unrecovered stale runs.",
            f"attention={stale}",
        )
    )

    open_circuits = [item for item in list_circuits() if item.get("state") == "OPEN"]
    checks.append(
        _check(
            "provider_availability",
            _status(not open_circuits, warn=False),
            "Inspect open circuit breakers before dispatching."
            if open_circuits
            else "No open circuit breakers.",
            ",".join(str(item["name"]) for item in open_circuits),
        )
    )

    processes = inspect_processes(repo_root=str(root))
    listening = [
        row
        for row in processes
        if row.get("port") in {4173, 8787, 8788} and row.get("state") == "listening"
    ]
    if http_probe is not None:
        cp_url = os.environ.get("AXON_WATCH_CONTROL_PLANE_BASE_URL", "http://127.0.0.1:8787")
        checks.append(_probe_named(http_probe, f"{cp_url}/api/health", "control_plane"))
        watch_url = os.environ.get("AXON_WATCH_WATCH_SERVICE_BASE_URL", "http://127.0.0.1:8788")
        checks.append(_probe_named(http_probe, f"{watch_url}/internal/watch/health", "watch"))
        console_url = os.environ.get("AXON_WATCH_PUBLIC_BASE_URL", "http://127.0.0.1:4173")
        checks.append(_probe_named(http_probe, console_url, "frontend"))
    else:
        control_plane_listening = any(
            row.get("port") == 8787 and row.get("state") == "listening" for row in processes
        )
        checks.append(
            _check(
                "control_plane",
                _status(control_plane_listening),
                "Control plane is listening."
                if control_plane_listening
                else "Start the control plane with axonrestart or ./scripts/dev/up.sh.",
            )
        )
        watch_listening = any(
            row.get("port") == 8788 and row.get("state") == "listening" for row in processes
        )
        checks.append(
            _check(
                "watch",
                _status(watch_listening),
                "Axon Watch is listening."
                if watch_listening
                else "Start axon-watch if operators need live signals.",
            )
        )
        frontend_listening = any(
            row.get("port") in {4173, 5173} and row.get("state") == "listening"
            for row in processes
        )
        checks.append(
            _check(
                "frontend",
                _status(frontend_listening),
                "Console frontend is listening."
                if frontend_listening
                else "Start console-web or the Vite IDE preview.",
            )
        )

    disk = shutil.disk_usage(str(root))
    disk_ok = disk.free > 512 * 1024 * 1024
    checks.append(
        _check(
            "disk_space",
            _status(disk_ok),
            "Free disk space before dispatching workers." if not disk_ok else "Disk has at least 512MiB free.",
            f"free={disk.free}",
        )
    )

    git_dir = root / ".git"
    checks.append(
        _check(
            "git_state",
            _status(git_dir.exists()),
            "Run from a git checkout of axon-watch.",
        )
    )
    checks.append(
        _check(
            "self_heal_level",
            "PASS",
            f"Autonomy is {autonomy_label()} (level {configured_autonomy_level()}).",
        )
    )

    worst = "PASS"
    for check in checks:
        if check["status"] == "FAIL":
            worst = "FAIL"
            break
        if check["status"] == "BLOCKED":
            worst = "BLOCKED"
        elif check["status"] == "WARN" and worst == "PASS":
            worst = "WARN"

    return {
        "status": worst,
        "checks": checks,
        "processes": processes,
        "recovery": {
            "attention_count": stale,
            "counts": recovery.get("counts") or {},
        },
        "autonomy_level": configured_autonomy_level(),
        "listening_core_services": len(listening),
    }


def _probe_named(probe: HttpProbe, url: str, name: str) -> dict[str, Any]:
    return _probe_status(probe, url, name)


def _probe_status(probe: HttpProbe, url: str, name: str) -> dict[str, Any]:
    try:
        code, body = probe(url)
    except Exception as exc:  # noqa: BLE001 — doctor must classify probe errors
        return _check(name, "FAIL", f"Investigate {url}: {exc}", str(exc))
    ok = 200 <= int(code) < 300
    return _check(
        name,
        _status(ok),
        f"GET {url} returned HTTP {code}." if not ok else f"{name} is reachable.",
        (body or "")[:180],
    )
