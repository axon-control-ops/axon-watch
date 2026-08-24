"""Keep the named tunnel reconciled instead of starting it once at boot.

The previous autostart fired a single `tunnel_start` during watch startup, so a
cloudflared process that later exited stayed down until an operator noticed. A
phone cannot restart a tunnel that is already down, so recovery has to be
entirely host-side: this supervisor re-checks the process on an interval and
restarts it with bounded exponential backoff.
"""

from __future__ import annotations

import logging
import os
import random
import threading
import time

from app.signals.iso_time import utc_now_iso
from app.tunnel.cloudflared_installer import installer_diagnostics
from app.tunnel.native_process import managed_process_snapshot
from app.tunnel.slice_registry import load_tunnel_slice
from app.tunnel.tunnel_control import TunnelControlError, tunnel_autostart_enabled, tunnel_start
from app.tunnel.tunnel_probe import build_tunnel_diagnostics, probe_local_origin

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL_SECONDS = 15.0
DEFAULT_BASE_BACKOFF_SECONDS = 5.0
DEFAULT_MAX_BACKOFF_SECONDS = 300.0
# Edge probes leave the machine, so they run on a slower cadence than the
# local process check that drives restarts.
DEFAULT_EDGE_CHECK_EVERY = 4


def _float_env(name: str, fallback: float) -> float:
    try:
        value = float(os.environ.get(name, "").strip())
    except ValueError:
        return fallback
    return value if value > 0 else fallback


class TunnelSupervisor:
    """Reconcile the managed cloudflared process toward 'running and reachable'."""

    def __init__(
        self,
        *,
        interval_seconds: float | None = None,
        base_backoff_seconds: float | None = None,
        max_backoff_seconds: float | None = None,
        edge_check_every: int = DEFAULT_EDGE_CHECK_EVERY,
    ) -> None:
        self.interval_seconds = interval_seconds or _float_env(
            "AXON_WATCH_TUNNEL_SUPERVISOR_INTERVAL", DEFAULT_INTERVAL_SECONDS
        )
        self.base_backoff_seconds = base_backoff_seconds or _float_env(
            "AXON_WATCH_TUNNEL_BACKOFF_BASE", DEFAULT_BASE_BACKOFF_SECONDS
        )
        self.max_backoff_seconds = max_backoff_seconds or _float_env(
            "AXON_WATCH_TUNNEL_BACKOFF_MAX", DEFAULT_MAX_BACKOFF_SECONDS
        )
        self.edge_check_every = max(1, int(edge_check_every))

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._tick = 0
        self._retry_count = 0
        self._next_retry_monotonic = 0.0
        self._paused_reason = ""
        self._state: dict[str, object] = {
            "supervising": False,
            "process_alive": False,
            "local_origin_healthy": None,
            "edge_reachable": None,
            "hostname": "",
            "hostname_correct": None,
            "last_connected_at": "",
            "last_checked_at": "",
            "retry_count": 0,
            "next_retry_in_seconds": 0.0,
            "failure_reason": "",
            "paused_reason": "",
        }

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> bool:
        if not tunnel_autostart_enabled():
            with self._lock:
                self._state["failure_reason"] = "autostart disabled"
            return False
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return True
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run,
                name="axon-watch-tunnel-supervisor",
                daemon=True,
            )
            self._state["supervising"] = True
            self._thread.start()
        return True

    def stop(self, *, timeout_seconds: float = 5.0) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=timeout_seconds)
        with self._lock:
            self._state["supervising"] = False
        self._thread = None

    def pause(self, reason: str = "stopped by operator") -> None:
        """Stop reconciling until resumed, so a deliberate stop actually sticks."""

        with self._lock:
            self._paused_reason = reason or "paused"
            self._state["paused_reason"] = self._paused_reason

    def resume(self) -> None:
        with self._lock:
            self._paused_reason = ""
            self._state["paused_reason"] = ""
            self._retry_count = 0
            self._next_retry_monotonic = 0.0

    def health(self) -> dict[str, object]:
        with self._lock:
            snapshot = dict(self._state)
        remaining = self._next_retry_monotonic - time.monotonic()
        snapshot["next_retry_in_seconds"] = round(max(0.0, remaining), 1)
        return snapshot

    # -- reconciliation ----------------------------------------------------

    def _backoff_seconds(self) -> float:
        delay = min(
            self.max_backoff_seconds,
            self.base_backoff_seconds * (2 ** max(0, self._retry_count - 1)),
        )
        # Jitter keeps a watch restart loop from hammering Cloudflare in lockstep.
        return delay * random.uniform(0.8, 1.2)

    def _record(self, **fields: object) -> None:
        with self._lock:
            self._state.update(fields)
            self._state["retry_count"] = self._retry_count
            self._state["last_checked_at"] = utc_now_iso()

    def _note_failure(self, reason: str) -> None:
        self._retry_count += 1
        delay = self._backoff_seconds()
        self._next_retry_monotonic = time.monotonic() + delay
        self._record(failure_reason=reason)
        logger.warning("tunnel supervisor: %s (retry %s in %.0fs)", reason, self._retry_count, delay)

    def reconcile_once(self) -> dict[str, object]:
        """One reconciliation pass. Never raises — the loop must survive anything."""

        with self._lock:
            paused = self._paused_reason
        if paused:
            self._record(process_alive=False, failure_reason="")
            return self.health()

        config = load_tunnel_slice()
        if config is None:
            self._record(process_alive=False, failure_reason="tunnel slice disabled")
            return self.health()

        self._tick += 1
        snapshot = managed_process_snapshot(config)
        process_alive = bool(snapshot.get("managed"))

        if process_alive:
            self._retry_count = 0
            self._next_retry_monotonic = 0.0
            self._record(
                process_alive=True,
                failure_reason="",
                last_connected_at=utc_now_iso(),
            )
            if self._tick % self.edge_check_every == 0:
                self._refresh_edge_state(config)
            return self.health()

        self._record(process_alive=False)

        if time.monotonic() < self._next_retry_monotonic:
            return self.health()

        origin = probe_local_origin(config)
        origin_healthy = bool(origin.get("healthy"))
        self._record(local_origin_healthy=origin_healthy)
        if not origin_healthy:
            # Fronting a dead origin just publishes 502s to the public hostname.
            self._note_failure(f"local origin unhealthy: {origin.get('detail') or 'unreachable'}")
            return self.health()

        try:
            started = tunnel_start(config)
        except TunnelControlError as exc:
            reason = str(exc)
            install = installer_diagnostics()
            if not install.get("installed") and "binary" in reason:
                reason = f"{reason} — run scripts/ops/install-cloudflared.sh"
            self._note_failure(reason)
            return self.health()
        except Exception as exc:  # noqa: BLE001 - loop must never die
            logger.exception("tunnel supervisor start failed")
            self._note_failure(f"unexpected error: {exc}")
            return self.health()

        if not started.get("running"):
            self._note_failure(str(started.get("detail") or "tunnel did not come up"))
            return self.health()

        self._retry_count = 0
        self._next_retry_monotonic = 0.0
        self._record(
            process_alive=True,
            failure_reason="",
            last_connected_at=utc_now_iso(),
        )
        logger.info("tunnel supervisor: restarted cloudflared")
        return self.health()

    def _refresh_edge_state(self, config: dict[str, object]) -> None:
        try:
            diagnostics = build_tunnel_diagnostics(config)
        except Exception:  # noqa: BLE001 - diagnostics are advisory
            logger.exception("tunnel supervisor diagnostics failed")
            return
        tunnel = diagnostics.get("tunnel")
        payload = tunnel if isinstance(tunnel, dict) else {}
        expected = str(config.get("stable_domain") or "").strip().lower()
        observed = str(payload.get("remote_ingress_hostname") or "").strip().lower()
        self._record(
            edge_reachable=bool(payload.get("public_health_ok")),
            hostname=observed or expected,
            hostname_correct=(observed == expected) if (observed and expected) else None,
        )

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.reconcile_once()
            except Exception:  # noqa: BLE001 - the supervisor must outlive its failures
                logger.exception("tunnel supervisor reconcile failed")
            self._stop_event.wait(self.interval_seconds)


_supervisor: TunnelSupervisor | None = None
_supervisor_lock = threading.Lock()


def get_tunnel_supervisor() -> TunnelSupervisor:
    global _supervisor
    with _supervisor_lock:
        if _supervisor is None:
            _supervisor = TunnelSupervisor()
        return _supervisor


def start_tunnel_supervisor() -> dict[str, object]:
    """Watch-startup entry point. Replaces the one-shot autostart attempt."""

    supervisor = get_tunnel_supervisor()
    started = supervisor.start()
    return {"supervising": started, **supervisor.health()}


def note_operator_stop(reason: str = "stopped by operator") -> None:
    """Suppress reconciliation after a deliberate stop."""

    if _supervisor is not None:
        _supervisor.pause(reason)


def note_operator_start() -> None:
    if _supervisor is not None:
        _supervisor.resume()


def tunnel_supervisor_health() -> dict[str, object]:
    return get_tunnel_supervisor().health()
