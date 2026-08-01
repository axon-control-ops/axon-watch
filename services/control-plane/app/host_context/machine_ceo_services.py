"""Optional host services Machine CEO may pause under memory pressure."""

from __future__ import annotations

import logging
import shutil
import subprocess
from typing import Any

logger = logging.getLogger(__name__)

# User systemd units that chew RAM when idle CI piles up (safe to stop under pressure).
_OPTIONAL_USER_UNITS = (
    "actions-runner-dashpro.service",
)

# Docker containers Axon can live without briefly (research / non-critical).
_OPTIONAL_DOCKER_CONTAINERS = (
    "axon-watch-searxng",
)


def _run(cmd: list[str], *, timeout: float = 20.0) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    out = ((proc.stdout or "") + (proc.stderr or "")).strip()
    return int(proc.returncode), out[:400]


def reclaim_optional_services() -> dict[str, Any]:
    """Stop idle CI runners + optional containers so Axon-X can boot under pressure."""
    stopped_units: list[str] = []
    stopped_containers: list[str] = []
    errors: list[str] = []

    systemctl = shutil.which("systemctl")
    if systemctl:
        for unit in _OPTIONAL_USER_UNITS:
            code, out = _run([systemctl, "--user", "is-active", unit], timeout=5.0)
            if code != 0 or out.strip() != "active":
                continue
            stop_code, stop_out = _run(
                [systemctl, "--user", "stop", unit],
                timeout=30.0,
            )
            if stop_code == 0:
                stopped_units.append(unit)
            else:
                errors.append(f"stop {unit}: {stop_out or stop_code}")

    docker = shutil.which("docker")
    if docker:
        for name in _OPTIONAL_DOCKER_CONTAINERS:
            code, out = _run(
                [docker, "inspect", "-f", "{{.State.Running}}", name],
                timeout=8.0,
            )
            if code != 0 or "true" not in out.lower():
                continue
            stop_code, stop_out = _run([docker, "stop", name], timeout=30.0)
            if stop_code == 0:
                stopped_containers.append(name)
            else:
                errors.append(f"docker stop {name}: {stop_out or stop_code}")

    # #region agent log
    try:
        import json
        import time

        with open(
            "/home/edp/axon-nvme/repos/axon-watch/.cursor/debug-db8bb4.log",
            "a",
            encoding="utf-8",
        ) as _dbg:
            _dbg.write(
                json.dumps(
                    {
                        "sessionId": "db8bb4",
                        "runId": "machine-ceo",
                        "hypothesisId": "D1",
                        "location": "machine_ceo_services.py:reclaim_optional_services",
                        "message": "optional service reclaim",
                        "data": {
                            "stopped_units": stopped_units,
                            "stopped_containers": stopped_containers,
                            "errors": errors[:4],
                        },
                        "timestamp": int(time.time() * 1000),
                    }
                )
                + "\n"
            )
    except Exception:
        pass
    # #endregion

    return {
        "ok": not errors,
        "stopped_units": stopped_units,
        "stopped_containers": stopped_containers,
        "errors": errors,
    }


__all__ = ["reclaim_optional_services"]
