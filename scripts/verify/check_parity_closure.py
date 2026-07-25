#!/usr/bin/env python3
"""Validate parity closure order and snapshot promotion consistency."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ORDER_FILE = REPO_ROOT / "config" / "parity-closure-order.json"
SNAPSHOT_FILE = REPO_ROOT / "config" / "parity-snapshot.json"
ROADMAP_FILE = REPO_ROOT / "docs" / "PARITY_CLOSURE_ROADMAP.md"


def validate_closure_order() -> list[str]:
    errors: list[str] = []
    if not ORDER_FILE.is_file():
        return [f"missing closure order: {ORDER_FILE.relative_to(REPO_ROOT)}"]
    if not ROADMAP_FILE.is_file():
        errors.append(f"missing roadmap: {ROADMAP_FILE.relative_to(REPO_ROOT)}")

    order = json.loads(ORDER_FILE.read_text(encoding="utf-8"))
    slices = order.get("slices")
    if not isinstance(slices, list) or not slices:
        return errors + ["parity-closure-order slices must be a non-empty list"]

    snapshot = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
    behavior_by_id = {entry["id"]: entry for entry in snapshot.get("behaviors", [])}

    seen: set[str] = set()
    done_count = 0
    for entry in slices:
        slice_id = str(entry.get("id", "")).strip()
        if not slice_id:
            errors.append("slice missing id")
            continue
        if slice_id in seen:
            errors.append(f"duplicate slice id: {slice_id}")
        seen.add(slice_id)

        status = str(entry.get("status", "")).strip()
        if status not in {"pending", "done", "in_progress"}:
            errors.append(f"{slice_id}: invalid status {status!r}")

        parity_ids = entry.get("parity_ids") or []
        if status == "done":
            done_count += 1
            for parity_id in parity_ids:
                row = behavior_by_id.get(parity_id)
                if row is None:
                    errors.append(f"{slice_id}: unknown parity id {parity_id!r}")
                    continue
                if row.get("status") != "verified":
                    errors.append(
                        f"{slice_id} is done but snapshot row {parity_id!r} is {row.get('status')!r}"
                    )

    next_slice = str(order.get("next_slice", "")).strip()
    pending = [entry["id"] for entry in slices if entry.get("status") == "pending"]
    if pending and next_slice != pending[0]:
        errors.append(f"next_slice should be {pending[0]!r}, got {next_slice!r}")
    if not pending and next_slice not in {"", "none", "complete"}:
        errors.append(f"unexpected next_slice when no pending slices: {next_slice!r}")

    summary = snapshot.get("summary", {})
    verified = sum(1 for row in snapshot.get("behaviors", []) if row.get("status") == "verified")
    partial = sum(1 for row in snapshot.get("behaviors", []) if row.get("status") == "partially_verified")
    if summary.get("verified_v1") != verified:
        errors.append(f"summary.verified_v1 ({summary.get('verified_v1')}) != counted {verified}")
    if summary.get("partially_verified") != partial:
        errors.append(
            f"summary.partially_verified ({summary.get('partially_verified')}) != counted {partial}"
        )

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv or sys.argv[1:])
    errors = validate_closure_order()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    order = json.loads(ORDER_FILE.read_text(encoding="utf-8"))
    print(f"parity closure order valid; next slice={order.get('next_slice')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
