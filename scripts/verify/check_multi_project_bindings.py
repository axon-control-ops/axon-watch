"""Validate multi-project workspace bindings contract."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.verify.common import CheckResult, emit, load_json

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC_PATH = REPO_ROOT / "config" / "multi-project-bindings-contract.json"


def validate_multi_project_bindings(*, spec: dict[str, object] | None = None) -> CheckResult:
    spec = spec or load_json(DEFAULT_SPEC_PATH)
    bindings_path = REPO_ROOT / str(spec["bindings_file"])
    if not bindings_path.is_file():
        return CheckResult(
            name="multi_project_bindings",
            status="fail",
            message=f"missing bindings file: {spec['bindings_file']}",
        )

    payload = load_json(bindings_path)
    bindings = payload.get("bindings")
    if not isinstance(bindings, dict):
        return CheckResult(
            name="multi_project_bindings",
            status="fail",
            message="bindings file must contain bindings object",
        )

    required_ids = list(spec["required_workspace_ids"])
    missing = [workspace_id for workspace_id in required_ids if workspace_id not in bindings]
    if missing:
        return CheckResult(
            name="multi_project_bindings",
            status="fail",
            message="required workspace bindings missing",
            details=[f"missing={missing}"],
        )

    for workspace_id in required_ids:
        entry = bindings[workspace_id]
        if not isinstance(entry, dict):
            return CheckResult(
                name="multi_project_bindings",
                status="fail",
                message=f"{workspace_id} binding must be an object",
            )
        project_root = str(entry.get("project_root", "")).strip()
        if not project_root:
            return CheckResult(
                name="multi_project_bindings",
                status="fail",
                message=f"{workspace_id} missing project_root",
            )

    handoff = spec.get("handoff_proof", {})
    source_id = str(handoff.get("source_workspace_id", "")).strip()
    target_id = str(handoff.get("target_workspace_id", "")).strip()
    if source_id not in bindings or target_id not in bindings:
        return CheckResult(
            name="multi_project_bindings",
            status="fail",
            message="handoff proof workspaces must exist in bindings",
        )

    return CheckResult(
        name="multi_project_bindings",
        status="pass",
        message=f"all {len(required_ids)} required workspace bindings present",
        details=[f"spec={DEFAULT_SPEC_PATH.relative_to(REPO_ROOT)}"],
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", help="multi-project bindings contract path")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    spec_path = Path(args.spec) if args.spec else DEFAULT_SPEC_PATH
    spec = load_json(spec_path)
    return emit(validate_multi_project_bindings(spec=spec))


if __name__ == "__main__":
    raise SystemExit(main())
