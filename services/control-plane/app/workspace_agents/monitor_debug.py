"""Gate 10 — generic monitor/debug adapters behind project.axon.yaml."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class IncidentSignal:
    source: str
    severity: str
    message: str
    fingerprint: str
    evidence_uris: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReproductionBundle:
    incident_fingerprint: str
    steps: list[str]
    probes: dict[str, str]
    artifact_uris: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DebugTaskPlan:
    goal: str
    acceptance_criteria: str
    reproduction: ReproductionBundle
    verifier_checks: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "acceptance_criteria": self.acceptance_criteria,
            "reproduction": self.reproduction.to_dict(),
            "verifier_checks": list(self.verifier_checks),
        }


def normalize_observability_sources(contract: dict[str, Any]) -> dict[str, list[str]]:
    obs = contract.get("observability") or {}
    return {
        "logs": [str(x) for x in (obs.get("logs") or [])],
        "metrics": [str(x) for x in (obs.get("metrics") or [])],
        "traces": [str(x) for x in (obs.get("traces") or [])],
    }


def incident_to_debug_task(
    signal: IncidentSignal,
    *,
    contract: dict[str, Any],
) -> DebugTaskPlan:
    level = str(contract.get("certification_level") or "inspect_only")
    if level not in {"monitor_debug", "stage_recover", "bounded_production", "repair", "build"}:
        # Inspect-only projects may still file a task, but without auto-repair authority.
        pass
    sources = normalize_observability_sources(contract)
    steps = [
        f"Capture signal {signal.fingerprint} from {signal.source}",
        "Collect matching logs/metrics/traces from project contract sources",
        "Reproduce in an isolated worktree",
        "Apply fix; run verifier checks; prove signal clear",
    ]
    probes = {
        "logs": ",".join(sources["logs"]) or "none",
        "metrics": ",".join(sources["metrics"]) or "none",
        "traces": ",".join(sources["traces"]) or "none",
        "health": ",".join(str(x) for x in (contract.get("health_probes") or [])) or "none",
    }
    required = list((contract.get("verifier") or {}).get("required_checks") or ["test"])
    return DebugTaskPlan(
        goal=f"Repair incident: {signal.message[:120]}",
        acceptance_criteria=(
            "deterministic reproduction attached; verifier checks pass; "
            f"signal {signal.fingerprint} cleared with evidence"
        ),
        reproduction=ReproductionBundle(
            incident_fingerprint=signal.fingerprint,
            steps=steps,
            probes=probes,
            artifact_uris=list(signal.evidence_uris),
        ),
        verifier_checks=required,
    )


def signal_clear_proof(
    *,
    fingerprint: str,
    remaining_signals: list[IncidentSignal],
) -> dict[str, Any]:
    still = [s for s in remaining_signals if s.fingerprint == fingerprint]
    return {
        "fingerprint": fingerprint,
        "cleared": len(still) == 0,
        "remaining": len(still),
    }
