#!/usr/bin/env python3
"""Validate the final parity snapshot used by TEST-10."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_FILE = REPO_ROOT / "config" / "parity-snapshot.json"
DECISION_FILE = REPO_ROOT / "docs" / "CUTOVER_DECISION.md"
VERIFICATION_FILE = REPO_ROOT / "docs" / "FINAL_PARITY_VERIFICATION.md"
CUTOVER_TODO = REPO_ROOT / "docs" / "AXON_X_CUTOVER_TODO.md"

REQUIRED_BEHAVIOR_IDS = {
    "run_stop_resume",
    "approval_boundaries",
    "review_ready_state",
    "workspace_handoffs",
    "real_project_workspace_connection",
    "operator_vs_ide_mode_semantics",
    "dock_behavior",
    "runtime_summary_behavior",
    "initial_shell_boot_expectations",
    "signal_inbox_consistency",
    "desktop_and_browser_startup",
    "kairo_watch_rules",
    "spoken_high_value_alerts",
    "delivery_receipts_operator_attention",
    "executive_operator_rhythm",
    "kairo_persona_operator_copy",
    "mobile_operator_cockpit_compactness",
    "watch_connectors_runtime_awareness",
    "watch_command_event_status_depth",
}

ALLOWED_STATUSES = {"verified", "partially_verified"}
ALLOWED_DECISIONS = {"bounded_cutover_approved", "full_retirement_approved"}


def validate_snapshot() -> list[str]:
    errors: list[str] = []
    if not SNAPSHOT_FILE.is_file():
        return [f"missing snapshot: {SNAPSHOT_FILE.relative_to(REPO_ROOT)}"]

    payload = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
    decision = payload.get("decision")
    if decision not in ALLOWED_DECISIONS:
        errors.append(f"invalid decision: {decision!r}")

    if payload.get("full_axon_local_retirement") is True and decision != "full_retirement_approved":
        errors.append("full_axon_local_retirement=true requires full_retirement_approved decision")

    behaviors = payload.get("behaviors")
    if not isinstance(behaviors, list):
        return errors + ["behaviors must be a list"]

    seen_ids: set[str] = set()
    verified = 0
    partial = 0
    for entry in behaviors:
        if not isinstance(entry, dict):
            errors.append("each behavior entry must be an object")
            continue
        behavior_id = str(entry.get("id", "")).strip()
        status = str(entry.get("status", "")).strip()
        if not behavior_id:
            errors.append("behavior missing id")
            continue
        if behavior_id in seen_ids:
            errors.append(f"duplicate behavior id: {behavior_id}")
        seen_ids.add(behavior_id)
        if status not in ALLOWED_STATUSES:
            errors.append(f"{behavior_id}: invalid status {status!r}")
        elif status == "verified":
            verified += 1
        else:
            partial += 1
        evidence = entry.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{behavior_id}: evidence must be a non-empty list")

    missing = sorted(REQUIRED_BEHAVIOR_IDS - seen_ids)
    extra = sorted(seen_ids - REQUIRED_BEHAVIOR_IDS)
    if missing:
        errors.append(f"missing behavior ids: {', '.join(missing)}")
    if extra:
        errors.append(f"unexpected behavior ids: {', '.join(extra)}")

    summary = payload.get("summary", {})
    if summary.get("total_behaviors") != len(REQUIRED_BEHAVIOR_IDS):
        errors.append("summary.total_behaviors must equal must-keep behavior count")
    if summary.get("verified_v1") != verified:
        errors.append(f"summary.verified_v1 ({summary.get('verified_v1')}) != counted verified ({verified})")
    if summary.get("partially_verified") != partial:
        errors.append(
            f"summary.partially_verified ({summary.get('partially_verified')}) != counted partial ({partial})"
        )

    gates = payload.get("required_gates_passed", [])
    for index in range(10):
        gate = f"TEST-{index}"
        if gate not in gates:
            errors.append(f"required_gates_passed missing {gate}")

    blockers = payload.get("blockers_for_full_retirement", [])
    if not isinstance(blockers, list):
        errors.append("blockers_for_full_retirement must be a list")
    elif payload.get("full_axon_local_retirement") is False and len(blockers) < 1:
        errors.append(
            "blockers_for_full_retirement must be non-empty when full retirement is not approved"
        )

    if decision == "bounded_cutover_approved" and payload.get("full_axon_local_retirement") is not False:
        errors.append("bounded_cutover_approved requires full_axon_local_retirement=false")

    if not DECISION_FILE.is_file():
        errors.append(f"missing decision doc: {DECISION_FILE.relative_to(REPO_ROOT)}")
    if not VERIFICATION_FILE.is_file():
        errors.append(f"missing verification doc: {VERIFICATION_FILE.relative_to(REPO_ROOT)}")

    if CUTOVER_TODO.is_file():
        todo = CUTOVER_TODO.read_text(encoding="utf-8")
        if "Final parity verification and cutover decision" not in todo:
            errors.append("cutover todo missing final slice heading")

    if VERIFICATION_FILE.is_file():
        verification = VERIFICATION_FILE.read_text(encoding="utf-8")
        if "parity-snapshot.json" not in verification:
            errors.append("FINAL_PARITY_VERIFICATION must reference parity-snapshot.json")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv or sys.argv[1:])
    errors = validate_snapshot()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    payload = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
    summary = payload["summary"]
    print(
        "parity snapshot valid: "
        f"{summary['verified_v1']} verified, "
        f"{summary['partially_verified']} partially_verified, "
        f"decision={payload['decision']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
