"""Native start/stop control for the Cloudflare tunnel process."""

from __future__ import annotations

from app.tunnel.native_process import (
    managed_process_snapshot,
    start_managed_process,
    stop_managed_process,
)
from app.tunnel.slice_registry import load_tunnel_slice
from app.tunnel.tunnel_credentials import load_tunnel_vault_secrets, resolve_cloudflare_tunnel_token_state
from app.tunnel.tunnel_probe import build_tunnel_diagnostics


class TunnelControlError(ValueError):
    pass


def _resolved_tunnel_token() -> str:
    vault_secrets = load_tunnel_vault_secrets()
    stored_token = str(vault_secrets.get("cloudflare_tunnel_token") or "")
    token_state = resolve_cloudflare_tunnel_token_state(
        stored_token,
        vault_secrets=vault_secrets,
    )
    return str(token_state.get("token") or "")


def tunnel_status(config: dict[str, object] | None = None) -> dict[str, object]:
    config = config or load_tunnel_slice() or {}
    diagnostics = build_tunnel_diagnostics(config)
    tunnel = diagnostics.get("tunnel")
    tunnel_payload = tunnel if isinstance(tunnel, dict) else {}
    managed = managed_process_snapshot(config)
    return {
        "running": bool(tunnel_payload.get("process_running")) or bool(managed["managed"]),
        "url": str(tunnel_payload.get("tunnel_url") or ""),
        "mode": str(tunnel_payload.get("mode") or "trycloudflare"),
        "named_tunnel_ready": bool(tunnel_payload.get("named_tunnel_ready")),
        "auth_source": str(tunnel_payload.get("auth_source") or "missing"),
        "binary_path": str(tunnel_payload.get("binary_path") or ""),
        "status": str(diagnostics.get("status") or "unknown"),
        "detail": str(diagnostics.get("detail") or ""),
        "control_backend": "native",
        **managed,
    }


def tunnel_start(config: dict[str, object] | None = None) -> dict[str, object]:
    config = config or load_tunnel_slice() or {}
    status = tunnel_status(config)
    if status.get("running"):
        status["msg"] = (
            "Tunnel is already running but is not managed by Axon-X"
            if not status.get("managed")
            else "Already running"
        )
        return status
    mode = str(status.get("mode") or "trycloudflare")
    if mode == "external":
        status["msg"] = "External tunnel mode does not start a local process"
        return status
    binary_path = str(status.get("binary_path") or "")
    if not binary_path:
        raise TunnelControlError("cloudflared binary not found")
    token = _resolved_tunnel_token() if mode == "named" else ""
    if mode == "named" and not token:
        raise TunnelControlError("Named tunnel mode needs a Cloudflare tunnel token")
    try:
        pid = start_managed_process(
            config,
            binary_path=binary_path,
            token=token,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        raise TunnelControlError(str(exc) or "tunnel start failed") from exc
    snapshot = tunnel_status(config)
    snapshot["msg"] = f"Tunnel started natively (PID {pid})"
    return snapshot


def tunnel_stop(config: dict[str, object] | None = None) -> dict[str, object]:
    config = config or load_tunnel_slice() or {}
    status = tunnel_status(config)
    if not status.get("managed"):
        if status.get("running"):
            raise TunnelControlError(
                "Tunnel process is running but is not managed by Axon-X; stop the legacy owner first"
            )
        status["msg"] = "Already stopped"
        return status
    try:
        stop_managed_process(config)
    except OSError as exc:
        raise TunnelControlError(str(exc) or "tunnel stop failed") from exc
    snapshot = tunnel_status(config)
    snapshot["msg"] = "Tunnel stopped"
    return snapshot
