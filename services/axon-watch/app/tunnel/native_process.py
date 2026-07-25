"""Own the cloudflared process without depending on another checkout."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _state_dir() -> Path:
    configured = os.environ.get("AXON_WATCH_STATE_DIR", ".local/state").strip()
    path = Path(configured or ".local/state").expanduser()
    if not path.is_absolute():
        path = (_repo_root() / path).resolve()
    return path


def _expand_path(raw: object, fallback: Path) -> Path:
    expanded = os.path.expandvars(str(raw or "").strip())
    return Path(expanded).expanduser() if expanded and "$" not in expanded else fallback


def process_state_path(config: dict[str, object]) -> Path:
    return _expand_path(
        config.get("native_process_state_path"),
        _state_dir() / "tunnel" / "cloudflared-process.json",
    )


def process_log_path(config: dict[str, object]) -> Path:
    return _expand_path(
        config.get("native_log_path"),
        _state_dir() / "tunnel" / "cloudflared.log",
    )


def _local_origin(config: dict[str, object]) -> str:
    configured = str(config.get("local_origin_url") or "").strip().rstrip("/")
    if configured:
        return configured
    health_url = str(config.get("local_health_url") or "").strip()
    parsed = urlsplit(health_url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return "http://127.0.0.1:4173"


def build_cloudflared_command(
    config: dict[str, object],
    binary_path: str,
    *,
    token: str = "",
) -> tuple[list[str], dict[str, str]]:
    mode = str(config.get("tunnel_mode") or "trycloudflare").strip().lower()
    env = os.environ.copy()
    if mode == "named":
        if not token:
            raise ValueError("Named tunnel mode needs a Cloudflare tunnel token")
        env["TUNNEL_TOKEN"] = token
        return [binary_path, "--no-autoupdate", "tunnel", "run"], env
    if mode == "trycloudflare":
        return [
            binary_path,
            "tunnel",
            "--url",
            _local_origin(config),
            "--no-autoupdate",
        ], env
    raise ValueError(f"Tunnel mode {mode!r} does not start a local cloudflared process")


def _read_process_state(config: dict[str, object]) -> dict[str, object]:
    path = process_state_path(config)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_process_state(
    config: dict[str, object],
    *,
    pid: int,
    binary_path: str,
) -> None:
    path = process_state_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(f"{path.suffix}.tmp")
    pending.write_text(
        json.dumps(
            {
                "pid": pid,
                "binary_path": binary_path,
                "process_start_ticks": _process_start_ticks(pid),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    pending.chmod(0o600)
    pending.replace(path)


def _clear_process_state(config: dict[str, object]) -> None:
    try:
        process_state_path(config).unlink()
    except FileNotFoundError:
        pass


def _process_command(pid: int) -> str:
    proc_cmdline = Path(f"/proc/{pid}/cmdline")
    try:
        return proc_cmdline.read_bytes().replace(b"\0", b" ").decode(errors="replace")
    except OSError:
        pass
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="],
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (result.stdout or "").strip()


def _process_start_ticks(pid: int) -> str:
    try:
        after_name = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").rsplit(")", 1)[1]
        fields = after_name.split()
        return fields[19] if len(fields) > 19 else ""
    except (OSError, IndexError):
        return ""


def _matches_managed_process(
    pid: int,
    binary_path: str,
    *,
    process_start_ticks: str = "",
) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    if process_start_ticks and _process_start_ticks(pid) != process_start_ticks:
        return False
    command = _process_command(pid)
    return bool(command) and Path(binary_path).name in command and "tunnel" in command


def managed_process_snapshot(config: dict[str, object]) -> dict[str, object]:
    state = _read_process_state(config)
    try:
        pid = int(state.get("pid") or 0)
    except (TypeError, ValueError):
        pid = 0
    binary_path = str(state.get("binary_path") or "")
    start_ticks = str(state.get("process_start_ticks") or "")
    running = _matches_managed_process(
        pid,
        binary_path,
        process_start_ticks=start_ticks,
    )
    if state and not running:
        _clear_process_state(config)
    return {
        "managed": running,
        "pid": pid if running else None,
        "process_state_path": str(process_state_path(config)),
        "log_path": str(process_log_path(config)),
    }


def _reap_process(process: subprocess.Popen[bytes]) -> None:
    process.wait()


def start_managed_process(
    config: dict[str, object],
    *,
    binary_path: str,
    token: str = "",
) -> int:
    existing = managed_process_snapshot(config)
    if existing["managed"]:
        return int(existing["pid"])

    command, env = build_cloudflared_command(config, binary_path, token=token)
    log_path = process_log_path(config)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab", buffering=0) as log_file:
        log_path.chmod(0o600)
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True,
        )
    time.sleep(0.2)
    return_code = process.poll()
    if return_code is not None:
        raise RuntimeError(f"cloudflared exited during startup with status {return_code}")

    try:
        _write_process_state(config, pid=process.pid, binary_path=binary_path)
    except OSError:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=2)
        raise
    threading.Thread(target=_reap_process, args=(process,), daemon=True).start()
    return process.pid


def stop_managed_process(
    config: dict[str, object],
    *,
    timeout_seconds: float = 5.0,
) -> bool:
    snapshot = managed_process_snapshot(config)
    if not snapshot["managed"]:
        return False
    pid = int(snapshot["pid"])
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        _clear_process_state(config)
        return True
    deadline = time.monotonic() + timeout_seconds
    state = _read_process_state(config)
    binary_path = str(state.get("binary_path") or "")
    start_ticks = str(state.get("process_start_ticks") or "")
    while time.monotonic() < deadline:
        if not _matches_managed_process(
            pid,
            binary_path,
            process_start_ticks=start_ticks,
        ):
            _clear_process_state(config)
            return True
        time.sleep(0.1)
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    _clear_process_state(config)
    return True
