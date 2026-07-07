"""Start/stop Cloudflare tunnel via axon-local tunnel.sh when available."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from app.tunnel.slice_registry import load_tunnel_slice
from app.tunnel.tunnel_probe import build_tunnel_diagnostics


class TunnelControlError(ValueError):
    pass


def _expand_root(raw: str) -> Path:
    expanded = os.path.expandvars(str(raw or "").strip())
    return Path(expanded).expanduser() if expanded else Path()


def _tunnel_script(config: dict[str, object]) -> Path | None:
    root = _expand_root(str(config.get("axon_local_root") or ""))
    if not root.is_dir():
        return None
    script = root / "tunnel.sh"
    return script if script.is_file() else None


def tunnel_status(config: dict[str, object] | None = None) -> dict[str, object]:
    diagnostics = build_tunnel_diagnostics(config)
    tunnel = diagnostics.get("tunnel")
    tunnel_payload = tunnel if isinstance(tunnel, dict) else {}
    return {
        "running": bool(tunnel_payload.get("process_running")),
        "url": str(tunnel_payload.get("tunnel_url") or ""),
        "mode": str(tunnel_payload.get("mode") or "trycloudflare"),
        "named_tunnel_ready": bool(tunnel_payload.get("named_tunnel_ready")),
        "auth_source": str(tunnel_payload.get("auth_source") or "missing"),
        "binary_path": str(tunnel_payload.get("binary_path") or ""),
        "status": str(diagnostics.get("status") or "unknown"),
        "detail": str(diagnostics.get("detail") or ""),
    }


def _run_tunnel_script(config: dict[str, object], command: str) -> dict[str, object]:
    script = _tunnel_script(config)
    if script is None:
        raise TunnelControlError(
            "axon-local tunnel.sh not found; set AXON_LOCAL_ROOT to the axon-local checkout"
        )

    env = os.environ.copy()
    token = (
        os.environ.get("AXON_CLOUDFLARE_TUNNEL_TOKEN")
        or os.environ.get("CLOUDFLARE_TUNNEL_TOKEN")
        or ""
    )
    if token:
        env["AXON_CLOUDFLARE_TUNNEL_TOKEN"] = token
        env["CLOUDFLARE_TUNNEL_TOKEN"] = token

    try:
        result = subprocess.run(
            [str(script), command],
            cwd=str(script.parent),
            capture_output=True,
            text=True,
            timeout=90,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise TunnelControlError("tunnel command timed out") from exc
    except OSError as exc:
        raise TunnelControlError(str(exc) or "tunnel command failed") from exc

    output = "\n".join(
        line.strip()
        for line in (result.stdout or result.stderr or "").splitlines()
        if line.strip()
    )
    if result.returncode != 0:
        raise TunnelControlError(output or f"tunnel {command} failed")

    snapshot = tunnel_status(config)
    snapshot["msg"] = output or f"Tunnel {command} completed"
    return snapshot


def tunnel_start(config: dict[str, object] | None = None) -> dict[str, object]:
    config = config or load_tunnel_slice() or {}
    status = tunnel_status(config)
    if status.get("running"):
        status["msg"] = "Already running"
        return status
    if not status.get("named_tunnel_ready"):
        raise TunnelControlError("Named tunnel mode needs a Cloudflare tunnel token")
    return _run_tunnel_script(config, "start")


def tunnel_stop(config: dict[str, object] | None = None) -> dict[str, object]:
    config = config or load_tunnel_slice() or {}
    return _run_tunnel_script(config, "stop")
