"""VAXON fleet self-heal — detect, classify, dispatch, verify, prevent."""

from __future__ import annotations

from app.fleet_self_heal.classify import (
    FailureSignature,
    build_fingerprint,
    classify_failure_signature,
    quick_fleet_infra_marker_match,
)
from app.fleet_self_heal.config import (
    FleetSelfHealConfig,
    clear_config_cache_for_tests,
    load_fleet_self_heal_config,
)

__all__ = [
    "FailureSignature",
    "FleetSelfHealConfig",
    "build_fingerprint",
    "classify_failure_signature",
    "clear_config_cache_for_tests",
    "load_fleet_self_heal_config",
    "quick_fleet_infra_marker_match",
]
