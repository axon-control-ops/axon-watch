"""Validate G4.1 legacy connector inventory contract and cross-wiring."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.verify.common import CheckResult, emit, load_json

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC_PATH = REPO_ROOT / "config" / "legacy-connector-inventory.json"
WATCH_CONNECTORS_PATH = REPO_ROOT / "config" / "watch-connectors.json"
PARITY_SNAPSHOT_PATH = REPO_ROOT / "config" / "parity-snapshot.json"

ALLOWED_STATUSES = frozenset(
    {"migrated", "partial", "unmigrated", "replaced", "optional_fallback"}
)
ALLOWED_CATEGORIES = frozenset(
    {"health_probe", "child_project_integration", "legacy_surface", "runtime_capability"}
)
REQUIRED_ENTRY_FIELDS = (
    "id",
    "display_name",
    "category",
    "axon_x_status",
    "owner",
    "phase_g_slice",
    "probe",
    "fallback",
    "removal_criteria",
)


def _require_mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def validate_legacy_connector_inventory(
    *,
    spec: dict[str, object] | None = None,
    watch_connectors: dict[str, object] | None = None,
    parity_snapshot: dict[str, object] | None = None,
) -> CheckResult:
    spec = spec or load_json(DEFAULT_SPEC_PATH)
    watch_connectors = watch_connectors or load_json(WATCH_CONNECTORS_PATH)
    parity_snapshot = parity_snapshot or load_json(PARITY_SNAPSHOT_PATH)

    inventory = spec.get("inventory")
    if not isinstance(inventory, list) or not inventory:
        return CheckResult(
            name="legacy_connector_inventory",
            status="fail",
            message="inventory must be a non-empty list",
        )

    seen_ids: set[str] = set()
    unmigrated_ids: list[str] = []
    watch_connector_ids = set(
        str(key)
        for key in _require_mapping(watch_connectors.get("connectors"), "watch connectors").keys()
    )
    inventory_ids: set[str] = set()

    for index, raw_entry in enumerate(inventory):
        if not isinstance(raw_entry, dict):
            return CheckResult(
                name="legacy_connector_inventory",
                status="fail",
                message=f"inventory[{index}] must be an object",
            )
        entry = raw_entry
        missing = [field for field in REQUIRED_ENTRY_FIELDS if field not in entry]
        if missing:
            return CheckResult(
                name="legacy_connector_inventory",
                status="fail",
                message=f"inventory[{index}] missing fields: {', '.join(missing)}",
            )

        connector_id = str(entry["id"]).strip()
        if not connector_id:
            return CheckResult(
                name="legacy_connector_inventory",
                status="fail",
                message=f"inventory[{index}] has empty id",
            )
        if connector_id in seen_ids:
            return CheckResult(
                name="legacy_connector_inventory",
                status="fail",
                message=f"duplicate inventory id: {connector_id}",
            )
        seen_ids.add(connector_id)
        inventory_ids.add(connector_id)

        category = str(entry["category"])
        if category not in ALLOWED_CATEGORIES:
            return CheckResult(
                name="legacy_connector_inventory",
                status="fail",
                message=f"{connector_id}: invalid category {category}",
            )

        status = str(entry["axon_x_status"])
        if status not in ALLOWED_STATUSES:
            return CheckResult(
                name="legacy_connector_inventory",
                status="fail",
                message=f"{connector_id}: invalid axon_x_status {status}",
            )

        removal = str(entry["removal_criteria"]).strip()
        if len(removal) < 24:
            return CheckResult(
                name="legacy_connector_inventory",
                status="fail",
                message=f"{connector_id}: removal_criteria too short",
            )

        probe = _require_mapping(entry["probe"], f"{connector_id}.probe")
        probe_kind = str(probe.get("kind", "")).strip()
        if not probe_kind:
            return CheckResult(
                name="legacy_connector_inventory",
                status="fail",
                message=f"{connector_id}: probe.kind is required",
            )

        watch_connector_id = str(probe.get("watch_connector_id", "")).strip()
        if watch_connector_id:
            if watch_connector_id not in watch_connector_ids:
                return CheckResult(
                    name="legacy_connector_inventory",
                    status="fail",
                    message=(
                        f"{connector_id}: watch_connector_id {watch_connector_id} "
                        "missing from watch-connectors.json"
                    ),
                )

        if status in {"unmigrated", "partial", "optional_fallback"}:
            unmigrated_ids.append(connector_id)
            phase_slice = entry.get("phase_g_slice")
            if phase_slice is None or str(phase_slice).strip() == "":
                return CheckResult(
                    name="legacy_connector_inventory",
                    status="fail",
                    message=f"{connector_id}: phase_g_slice required for {status}",
                )

        if status == "migrated" and entry.get("phase_g_slice") not in (None, ""):
            return CheckResult(
                name="legacy_connector_inventory",
                status="fail",
                message=f"{connector_id}: migrated entries must not carry phase_g_slice",
            )

    for connector_id in sorted(watch_connector_ids):
        if connector_id not in inventory_ids:
            return CheckResult(
                name="legacy_connector_inventory",
                status="fail",
                message=f"watch connector {connector_id} missing from inventory",
            )

    full_retired = bool(parity_snapshot.get("full_axon_local_retirement"))
    blocker_map = spec.get("retirement_blocker_map")
    if not isinstance(blocker_map, dict):
        return CheckResult(
            name="legacy_connector_inventory",
            status="fail",
            message="retirement_blocker_map must be an object",
        )
    if not full_retired and not blocker_map:
        return CheckResult(
            name="legacy_connector_inventory",
            status="fail",
            message="retirement_blocker_map must be non-empty before full retirement",
        )

    snapshot_blockers = parity_snapshot.get("blockers_for_full_retirement")
    if not isinstance(snapshot_blockers, list):
        return CheckResult(
            name="legacy_connector_inventory",
            status="fail",
            message="parity-snapshot blockers_for_full_retirement must be a list",
        )
    if not full_retired and not snapshot_blockers:
        return CheckResult(
            name="legacy_connector_inventory",
            status="fail",
            message="parity-snapshot blockers_for_full_retirement must be non-empty before full retirement",
        )

    for blocker_text, mapped_ids in blocker_map.items():
        if blocker_text not in snapshot_blockers:
            return CheckResult(
                name="legacy_connector_inventory",
                status="fail",
                message=f"retirement_blocker_map key not in parity-snapshot: {blocker_text}",
            )
        if not isinstance(mapped_ids, list) or not mapped_ids:
            return CheckResult(
                name="legacy_connector_inventory",
                status="fail",
                message=f"retirement_blocker_map[{blocker_text}] must be a non-empty list",
            )
        unknown = [item for item in mapped_ids if str(item) not in inventory_ids]
        if unknown:
            return CheckResult(
                name="legacy_connector_inventory",
                status="fail",
                message=f"retirement_blocker_map references unknown ids: {unknown}",
            )

    if full_retired and blocker_map:
        return CheckResult(
            name="legacy_connector_inventory",
            status="fail",
            message="retirement_blocker_map must be empty once axon-local retirement is signed",
        )

    doc_path = REPO_ROOT / "docs" / "LEGACY_CONNECTOR_INVENTORY.md"
    if not doc_path.is_file():
        return CheckResult(
            name="legacy_connector_inventory",
            status="fail",
            message="missing docs/LEGACY_CONNECTOR_INVENTORY.md",
        )
    doc_text = doc_path.read_text(encoding="utf-8")
    if "G4.1" not in doc_text or "removal criteria" not in doc_text.lower():
        return CheckResult(
            name="legacy_connector_inventory",
            status="fail",
            message="LEGACY_CONNECTOR_INVENTORY.md missing G4.1 owner/probe/removal table",
        )

    return CheckResult(
        name="legacy_connector_inventory",
        status="pass",
        message="legacy connector inventory contract satisfied",
        details=[
            f"spec={DEFAULT_SPEC_PATH.relative_to(REPO_ROOT)}",
            f"entries={len(inventory)}",
            f"open_retirement_items={len(unmigrated_ids)}",
        ],
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", help="inventory JSON path")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    spec_path = Path(args.spec) if args.spec else DEFAULT_SPEC_PATH
    spec = load_json(spec_path)
    return emit(validate_legacy_connector_inventory(spec=spec))


if __name__ == "__main__":
    raise SystemExit(main())
