"""Seed and backfill helpers for AXON-X constitution registries."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from app.persistence import constitution_registry_store as registry

_ADR_FILE_RE = re.compile(r"ADR-(?P<number>\d{3})-.*\.md$")


@dataclass(frozen=True)
class CapabilitySeed:
    capability_id: str
    name: str
    description: str
    owner_role: str
    route_paths: tuple[str, ...] = ()


CAPABILITY_SEEDS: tuple[CapabilitySeed, ...] = (
    CapabilitySeed(
        "CAP-001",
        "Executive briefing and operator command",
        "Keep the operator informed with clear current-state summaries, next actions, and blockers.",
        "operator",
        ("/api/briefing",),
    ),
    CapabilitySeed(
        "CAP-007",
        "Evidence engine",
        "Index execution evidence from source receipts without duplicating the source-of-truth stores.",
        "control-plane",
        ("/api/operator/constitution/evidence", "/api/operator/constitution/evidence/backfill"),
    ),
    CapabilitySeed(
        "CAP-009",
        "Mission registry",
        "Represent operator goals as durable missions with success criteria, checkpoints, and Lead-plan links.",
        "lead",
        ("/api/operator/constitution/missions",),
    ),
    CapabilitySeed(
        "CAP-012",
        "Decision registry",
        "Record autonomous and operator-gated decisions with evidence references and confidence notes.",
        "control-plane",
        ("/api/operator/constitution/decisions",),
    ),
    CapabilitySeed(
        "CAP-018",
        "ADR registry",
        "Make architecture decisions queryable from canonical markdown ADRs and runtime policy records.",
        "architecture",
        ("/api/operator/constitution/adrs",),
    ),
    CapabilitySeed(
        "CAP-024",
        "Technical debt registry",
        "Capture known debt with severity, area, and evidence links so gaps do not disappear between runs.",
        "engineering",
        ("/api/operator/constitution/debt",),
    ),
    CapabilitySeed(
        "CAP-031",
        "Platform health registry",
        "Persist runtime health snapshots so agents can verify service posture before self-healing.",
        "control-plane",
        ("/api/operator/constitution/health",),
    ),
    CapabilitySeed(
        "CAP-034",
        "Autonomous attention loop",
        "Let VAXON detect safe recovery opportunities, capture receipts, and escalate real blockers honestly.",
        "vaxon",
        (),
    ),
    CapabilitySeed(
        "CAP-041",
        "Lead fan-out and worker dispatch",
        "Convert Lead plans into specialist work with auditable queued-run receipts and role-safe routing.",
        "lead",
        (),
    ),
    CapabilitySeed(
        "CAP-052",
        "Runtime policy and composer control",
        "Keep AUTO-mode runtime choices explicit, reversible, and visible across composers.",
        "operator",
        ("/api/workspaces/",),
    ),
    CapabilitySeed(
        "CAP-061",
        "Console constitution surface",
        "Expose constitution state read-only in the console for operators and agents.",
        "frontend",
        ("/api/operator/constitution",),
    ),
    CapabilitySeed(
        "CAP-070",
        "Constitution verification gate",
        "Fail fast when constitution registries, routes, tests, or auth guardrails drift.",
        "quality",
        (),
    ),
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _first_heading(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped.removeprefix("# ").strip() or fallback
    return fallback


def _status(text: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip().lower() == "## status":
            for candidate in lines[index + 1 : index + 6]:
                cleaned = candidate.strip()
                if cleaned:
                    return cleaned.lower()
    return "proposed"


def seed_capabilities() -> int:
    count = 0
    for item in CAPABILITY_SEEDS:
        registry.upsert_capability(
            capability_id=item.capability_id,
            name=f"{item.capability_id} {item.name}",
            description=item.description,
            status="active",
            owner_role=item.owner_role,
            route_paths=list(item.route_paths),
            version="0.1.0",
        )
        count += 1
    return count


def backfill_adrs(*, adr_root: Path | None = None) -> int:
    root = adr_root or _repo_root() / "docs" / "adr"
    if not root.exists():
        return 0
    count = 0
    for path in sorted(root.glob("ADR-*.md")):
        match = _ADR_FILE_RE.match(path.name)
        if not match:
            continue
        text = path.read_text(encoding="utf-8")
        number = int(match.group("number"))
        registry.upsert_adr(
            number=number,
            title=_first_heading(text, fallback=path.stem),
            status=_status(text),
            doc_path=str(path.relative_to(_repo_root())) if path.is_relative_to(_repo_root()) else str(path),
            summary=text[:600],
        )
        count += 1
    return count


def seed_constitution_registries() -> dict[str, int]:
    return {
        "capabilities": seed_capabilities(),
        "adrs": backfill_adrs(),
    }
