"""Live Cloudflare tunnel diagnostics for connectors rail and remote control."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.probe_failure_detail import format_probe_failure
from app.signals.iso_time import utc_now_iso
from app.tunnel.cloudflared_binary import cloudflared_version, find_cloudflared_binary
from app.tunnel.native_process import managed_process_snapshot
from app.tunnel.slice_registry import load_tunnel_slice
from app.tunnel.tunnel_credentials import (
    load_tunnel_vault_secrets,
    named_tunnel_ready,
    resolve_cloudflare_tunnel_token_state,
)

_TRYCF_URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com", re.IGNORECASE)
# cloudflared logs embed remote config as escaped JSON inside config="...".
_REMOTE_INGRESS_RE = re.compile(
    r'"hostname"\s*:\s*"([^"]+)"\s*,\s*"service"\s*:\s*"([^"]+)"',
    re.IGNORECASE,
)
_AXON_X_HEALTH_MARKERS = ("control-plane", '"service": "control-plane"', '"service":"control-plane"')
_AXON_LOCAL_HEALTH_MARKERS = ('"port": 7734', '"port":7734', "axon-local", "devbrain")
_PROBE_HEADERS = {
    "Accept": "application/json, */*",
    # Cloudflare often blocks the default Python-urllib User-Agent with 403.
    "User-Agent": "Axon-X-TunnelProbe/1.0 (+https://axon.edudashpro.org.za)",
}


def _expand_path(raw: str) -> Path:
    text = str(raw or "").strip()
    # Slice JSON uses ${AXON_WATCH_STATE_DIR}; default it when unset so log probes work.
    if "${AXON_WATCH_STATE_DIR}" in text and not os.environ.get("AXON_WATCH_STATE_DIR"):
        text = text.replace("${AXON_WATCH_STATE_DIR}", ".local/state")
    return Path(os.path.expandvars(text)).expanduser()


def _probe_http(url: str, *, timeout_seconds: float = 3.0) -> tuple[bool, int | None, str]:
    started = time.monotonic()
    try:
        request = Request(url, headers=dict(_PROBE_HEADERS))
        with urlopen(request, timeout=timeout_seconds) as response:
            latency_ms = int((time.monotonic() - started) * 1000)
            if response.status != 200:
                return False, latency_ms, f"HTTP {response.status}"
            body = response.read(4096).decode("utf-8", errors="replace")
            if body.strip():
                try:
                    payload = json.loads(body)
                except json.JSONDecodeError:
                    payload = None
                if isinstance(payload, dict):
                    service_status = str(payload.get("status", "")).strip()
                    if service_status and service_status not in {"ok", "ready"}:
                        return False, latency_ms, f"status={service_status}"
            return True, latency_ms, "reachable"
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        latency_ms = int((time.monotonic() - started) * 1000)
        return False, latency_ms, format_probe_failure(exc, url)


def _classify_public_health_body(body: str) -> tuple[bool, str]:
    """Return (is_axon_x, detail) for a public /api/health body."""

    text = (body or "").strip()
    if not text:
        return False, "empty body"
    lowered = text.lower()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        service = str(payload.get("service") or "").strip().lower()
        if service == "control-plane":
            return True, "axon-x control-plane"
        runtime = payload.get("runtime")
        if isinstance(runtime, dict):
            repo_root = str(runtime.get("repo_root") or "").lower()
            if "axon-local" in repo_root or "devbrain" in repo_root:
                return False, "axon-local runtime"
        port = payload.get("port")
        if port in {7734, "7734"} and service != "control-plane":
            return False, "axon-local port marker"
        status = str(payload.get("status") or "").strip().lower()
        if status and status not in {"ok", "ready"}:
            return False, f"status={status}"
    if any(marker in lowered for marker in _AXON_LOCAL_HEALTH_MARKERS):
        return False, "axon-local markers"
    if any(marker in lowered for marker in _AXON_X_HEALTH_MARKERS):
        return True, "axon-x markers"
    return False, "unrecognized health body"


def _probe_public_axon_x(
    url: str, *, timeout_seconds: float = 3.0
) -> tuple[bool, int | None, str]:
    """Probe public health and require an Axon-X (control-plane) identity."""

    started = time.monotonic()
    try:
        request = Request(url, headers=dict(_PROBE_HEADERS))
        with urlopen(request, timeout=timeout_seconds) as response:
            latency_ms = int((time.monotonic() - started) * 1000)
            if response.status != 200:
                return False, latency_ms, f"HTTP {response.status}"
            body = response.read(4096).decode("utf-8", errors="replace")
            is_axon_x, detail = _classify_public_health_body(body)
            return is_axon_x, latency_ms, detail
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        latency_ms = int((time.monotonic() - started) * 1000)
        return False, latency_ms, format_probe_failure(exc, url)


def _tunnel_process_running(binary_path: str) -> bool:
    pattern = binary_path or "cloudflared"
    try:
        result = subprocess.run(
            ["pgrep", "-f", f"{pattern}.*tunnel"],
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return bool((result.stdout or "").strip())


def _cloudflared_process_count() -> int:
    """Count real cloudflared processes by exact comm name."""

    try:
        result = subprocess.run(
            ["pgrep", "-x", "cloudflared"],
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 0
    return len([line for line in (result.stdout or "").splitlines() if line.strip()])


def _remote_ingress_from_logs(paths: list[str]) -> tuple[str, str]:
    for raw in paths:
        path = _expand_path(raw)
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # Named-tunnel logs store config with escaped quotes (\"hostname\").
        normalized = text.replace('\\"', '"')
        matches = _REMOTE_INGRESS_RE.findall(normalized)
        if matches:
            hostname, service = matches[-1]
            return str(hostname).strip(), str(service).strip()
    return "", ""


def _read_tunnel_url_from_logs(paths: list[str]) -> str:
    for raw in paths:
        path = _expand_path(raw)
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        matches = _TRYCF_URL_RE.findall(text)
        if matches:
            return matches[-1]
    return ""


def _resolve_tunnel_url(config: dict[str, object], *, process_running: bool) -> str:
    if not process_running:
        return ""
    mode = str(config.get("tunnel_mode") or "trycloudflare").strip().lower()
    if mode == "named":
        return str(config.get("public_base_url") or "").strip()
    log_paths = config.get("tunnel_log_paths")
    if isinstance(log_paths, list):
        return _read_tunnel_url_from_logs([str(item) for item in log_paths])
    return ""


def probe_local_origin(config: dict[str, object] | None = None) -> dict[str, object]:
    """Check the local origin the tunnel fronts, without touching Cloudflare."""

    config = config or load_tunnel_slice() or {}
    url = str(config.get("local_health_url") or "").strip()
    if not url:
        origin = str(config.get("local_origin_url") or "http://127.0.0.1:4173").strip().rstrip("/")
        url = f"{origin}/api/health"
    healthy, latency_ms, detail = _probe_http(url)
    return {
        "healthy": healthy,
        "url": url,
        "latency_ms": latency_ms,
        "detail": detail,
    }


def build_tunnel_diagnostics(config: dict[str, object] | None = None) -> dict[str, object]:
    config = config or load_tunnel_slice() or {}
    checked_at = utc_now_iso()
    connector_id = str(config.get("connector_id") or "cloudflare_tunnel").strip()
    display_name = str(config.get("display_name") or "Cloudflare tunnel").strip()
    workspace_id = str(config.get("workspace_id") or "workspace_axon_watch").strip()
    tunnel_mode = str(config.get("tunnel_mode") or "trycloudflare").strip().lower()
    public_base_url = str(config.get("public_base_url") or "").strip().rstrip("/")
    vault_secrets = load_tunnel_vault_secrets()
    stored_token = str(vault_secrets.get("cloudflare_tunnel_token") or "")
    token_state = resolve_cloudflare_tunnel_token_state(
        stored_token,
        vault_secrets=vault_secrets,
    )

    candidates = config.get("binary_candidates")
    binary_candidates = (
        [str(item) for item in candidates]
        if isinstance(candidates, list)
        else ["cloudflared"]
    )
    binary_path = find_cloudflared_binary(binary_candidates)
    auth_source = str(token_state.get("source") or "missing")
    auth_ready = named_tunnel_ready(
        tunnel_mode=tunnel_mode,
        token_state=token_state,
        stored_value=stored_token,
    )
    managed_process = managed_process_snapshot(config)
    process_running = _tunnel_process_running(binary_path) or bool(managed_process["managed"])
    tunnel_url = _resolve_tunnel_url(config, process_running=process_running)
    process_count = _cloudflared_process_count()
    expected_origin = str(config.get("local_origin_url") or "http://127.0.0.1:4173").strip()
    log_paths_raw = config.get("tunnel_log_paths")
    log_paths = (
        [str(item) for item in log_paths_raw]
        if isinstance(log_paths_raw, list)
        else [str(config.get("log_path") or "")]
    )
    remote_log_paths = list(log_paths)
    managed_log = str(managed_process.get("log_path") or "").strip()
    if managed_log:
        remote_log_paths.append(managed_log)
    remote_hostname, remote_service = _remote_ingress_from_logs(remote_log_paths)
    ingress_matches_axon = bool(
        remote_service
        and (
            remote_service.rstrip("/") == expected_origin.rstrip("/")
            or remote_service.rstrip("/")
            in {
                "http://localhost:4173",
                "http://127.0.0.1:4173",
            }
        )
    )

    public_health_url = f"{public_base_url}/api/health" if public_base_url else ""
    public_ok = False
    public_latency_ms: int | None = None
    public_detail = ""
    if public_health_url and process_running and tunnel_mode == "named":
        public_ok, public_latency_ms, public_detail = _probe_public_axon_x(public_health_url)

    if not binary_path:
        status = "unavailable"
        detail = "cloudflared binary not found"
    elif not auth_ready:
        status = "unavailable"
        detail = f"tunnel token missing (auth={auth_source})"
    elif not process_running:
        status = "degraded"
        detail = f"tunnel stopped (auth={auth_source})"
        if process_count > 0:
            plural = "process" if process_count == 1 else "processes"
            detail = (
                f"{detail}; {process_count} cloudflared {plural} on host "
                "but none match the managed Axon-X tunnel"
            )
        if (
            tunnel_mode == "named"
            and remote_service
            and not ingress_matches_axon
        ):
            detail = (
                f"{detail}; remote ingress still points at {remote_service}; "
                f"expected {expected_origin}"
            )
    elif process_count > 1:
        status = "degraded"
        detail = (
            f"multiple cloudflared tunnel processes ({process_count}); "
            "disable root cloudflared.service for exclusive Axon-X ownership"
        )
    elif not managed_process["managed"]:
        status = "degraded"
        detail = "tunnel process is running but is not managed by Axon-X"
    elif tunnel_mode == "named" and public_health_url and not public_ok:
        status = "degraded"
        detail = (
            f"remote ingress unhealthy ({public_detail}); local Axon-X unaffected"
        )
    elif (
        tunnel_mode == "named"
        and remote_service
        and not ingress_matches_axon
    ):
        status = "degraded"
        detail = (
            f"remote ingress still points at {remote_service}; "
            f"expected {expected_origin}"
        )
    elif tunnel_mode != "named" and process_running and not tunnel_url:
        status = "degraded"
        detail = "tunnel process up; trycloudflare URL not found in logs"
    else:
        status = "ok"
        if tunnel_url:
            detail = f"active {tunnel_url}"
        else:
            detail = "tunnel process running"
    if process_running and not managed_process["managed"] and "not managed" not in detail:
        detail = f"{detail}; process is not managed by Axon-X"

    latency_ms = public_latency_ms
    health_url = public_health_url or str(config.get("local_health_url") or "").strip()

    record: dict[str, object] = {
        "connector_id": connector_id,
        "display_name": display_name,
        "health_url": health_url,
        "required": bool(config.get("required", False)),
        "workspace_id": workspace_id,
        "last_checked_at": checked_at,
        "status": status,
        "detail": detail,
        "tunnel": {
            "mode": tunnel_mode,
            "binary_path": binary_path,
            "binary_version": cloudflared_version(binary_path),
            "auth_source": auth_source,
            "auth_ready": auth_ready,
            "named_tunnel_ready": auth_ready,
            "process_running": process_running,
            "process_count": process_count,
            "tunnel_url": tunnel_url,
            "public_base_url": public_base_url,
            "public_health_ok": public_ok,
            "public_health_detail": public_detail,
            "expected_origin": expected_origin,
            "remote_ingress_hostname": remote_hostname,
            "remote_ingress_service": remote_service,
            "ingress_matches_axon": ingress_matches_axon,
            "control_backend": "native",
            "managed_process": bool(managed_process["managed"]),
            "managed_pid": managed_process["pid"],
            "process_state_path": managed_process["process_state_path"],
            "log_path": managed_process["log_path"],
        },
    }
    if latency_ms is not None:
        record["latency_ms"] = latency_ms
    return record


def probe_cloudflare_tunnel(config: dict[str, object] | None = None) -> dict[str, object]:
    return build_tunnel_diagnostics(config)
