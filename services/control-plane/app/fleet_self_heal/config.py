"""Load VAXON fleet self-heal thresholds/routing from config/vaxon-fleet-repair.json."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FleetSelfHealConfig:
    enabled: bool
    dispatch_enabled: bool
    target_workspace_id: str
    owner_role: str
    escalate_role: str
    attempt_budget_per_dispatch: int
    max_dispatch_cycles: int
    window_hours: float
    repeat_occurrence_threshold: int
    breadth_pair_threshold: int
    min_scan_interval_seconds: float
    push_policy: str
    subsystem_role_overrides: dict[str, str] = field(default_factory=dict)

    def role_for_subsystem(self, subsystem: str) -> str:
        return self.subsystem_role_overrides.get(subsystem, self.owner_role)


_CACHE: FleetSelfHealConfig | None = None

_DEFAULT_CONFIG = FleetSelfHealConfig(
    enabled=True,
    dispatch_enabled=False,
    target_workspace_id="workspace_axon_watch",
    owner_role="watcher",
    escalate_role="lead",
    attempt_budget_per_dispatch=3,
    max_dispatch_cycles=3,
    window_hours=6.0,
    repeat_occurrence_threshold=2,
    breadth_pair_threshold=2,
    min_scan_interval_seconds=300.0,
    push_policy="draft_pr",
    subsystem_role_overrides={},
)


def _repo_root() -> Path:
    # …/services/control-plane/app/fleet_self_heal/config.py → parents[4] = repo root
    return Path(__file__).resolve().parents[4]


def default_config_path() -> Path:
    configured = os.environ.get("AXON_WATCH_FLEET_REPAIR_FILE", "").strip()
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            path = (_repo_root() / path).resolve()
        return path
    return (_repo_root() / "config" / "vaxon-fleet-repair.json").resolve()


def clear_config_cache_for_tests() -> None:
    global _CACHE
    _CACHE = None


def _as_int(value: Any, default: int, *, minimum: int = 1, maximum: int = 100) -> int:
    try:
        return max(minimum, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float, *, minimum: float = 0.0) -> float:
    try:
        return max(minimum, float(value))
    except (TypeError, ValueError):
        return default


def _config_from_payload(payload: dict[str, Any]) -> FleetSelfHealConfig:
    defaults = payload.get("defaults") if isinstance(payload.get("defaults"), dict) else {}
    overrides_raw = payload.get("subsystem_role_overrides")
    overrides = (
        {str(k): str(v).strip().lower() for k, v in overrides_raw.items()}
        if isinstance(overrides_raw, dict)
        else {}
    )
    return FleetSelfHealConfig(
        enabled=bool(payload.get("enabled", True)),
        dispatch_enabled=bool(payload.get("dispatch_enabled", False)),
        target_workspace_id=str(
            payload.get("target_workspace_id") or "workspace_axon_watch"
        ).strip()
        or "workspace_axon_watch",
        owner_role=str(defaults.get("owner_role") or "watcher").strip().lower() or "watcher",
        escalate_role=str(defaults.get("escalate_role") or "lead").strip().lower() or "lead",
        attempt_budget_per_dispatch=_as_int(
            defaults.get("attempt_budget_per_dispatch", 3), 3, minimum=1, maximum=32
        ),
        max_dispatch_cycles=_as_int(
            defaults.get("max_dispatch_cycles", 3), 3, minimum=1, maximum=32
        ),
        window_hours=_as_float(defaults.get("window_hours", 6), 6.0, minimum=0.25),
        repeat_occurrence_threshold=_as_int(
            defaults.get("repeat_occurrence_threshold", 2), 2, minimum=1, maximum=1000
        ),
        breadth_pair_threshold=_as_int(
            defaults.get("breadth_pair_threshold", 2), 2, minimum=1, maximum=1000
        ),
        min_scan_interval_seconds=_as_float(
            defaults.get("min_scan_interval_seconds", 300), 300.0, minimum=1.0
        ),
        push_policy=str(defaults.get("push_policy") or "draft_pr").strip() or "draft_pr",
        subsystem_role_overrides=overrides,
    )


def load_fleet_self_heal_config(
    *,
    path: Path | None = None,
    force_reload: bool = False,
) -> FleetSelfHealConfig:
    global _CACHE
    if _CACHE is not None and not force_reload and path is None:
        return _CACHE
    config_path = path or default_config_path()
    if not config_path.is_file():
        result = _DEFAULT_CONFIG
    else:
        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        result = _config_from_payload(payload if isinstance(payload, dict) else {})
    if path is None:
        _CACHE = result
    return result


__all__ = [
    "FleetSelfHealConfig",
    "clear_config_cache_for_tests",
    "default_config_path",
    "load_fleet_self_heal_config",
]
