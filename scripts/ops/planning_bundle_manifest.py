#!/usr/bin/env python3
"""Generate and validate the canonical docs/planning bundle manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PLANNING_DIR = REPO_ROOT / "docs" / "planning"
MANIFEST_FILE = PLANNING_DIR / "MANIFEST.json"
LEGACY_SOURCE = "axon-local/Plans/Axon-Watch/"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _planning_files() -> list[Path]:
    return sorted(
        path
        for path in PLANNING_DIR.iterdir()
        if path.is_file() and path.name.endswith(".md")
    )


def build_manifest() -> dict[str, object]:
    files = {
        path.name: {
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
        }
        for path in _planning_files()
    }
    return {
        "schema_version": 1,
        "canonical_home": "docs/planning/",
        "legacy_mirror": LEGACY_SOURCE,
        "generated_on": date.today().isoformat(),
        "file_count": len(files),
        "files": files,
    }


def write_manifest() -> dict[str, object]:
    PLANNING_DIR.mkdir(parents=True, exist_ok=True)
    payload = build_manifest()
    MANIFEST_FILE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def validate_manifest() -> list[str]:
    errors: list[str] = []
    if not MANIFEST_FILE.is_file():
        return [f"missing manifest: {MANIFEST_FILE.relative_to(REPO_ROOT)}"]

    payload = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    recorded = payload.get("files")
    if not isinstance(recorded, dict):
        return ["manifest.files must be an object"]

    current_paths = _planning_files()
    current_names = {path.name for path in current_paths}
    recorded_names = set(recorded.keys())

    missing = sorted(recorded_names - current_names)
    extra = sorted(current_names - recorded_names)
    if missing:
        errors.append(f"missing planning files: {', '.join(missing)}")
    if extra:
        errors.append(f"untracked planning files (regenerate manifest): {', '.join(extra)}")

    for path in current_paths:
        entry = recorded.get(path.name)
        if not isinstance(entry, dict):
            continue
        expected = str(entry.get("sha256", ""))
        actual = _sha256(path)
        if expected != actual:
            errors.append(f"hash mismatch for {path.name}")

    minimum = int(payload.get("file_count", 0))
    if len(current_names) < minimum:
        errors.append(f"expected at least {minimum} planning files, found {len(current_names)}")

    return errors


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("write", "validate"),
        help="write MANIFEST.json or validate the current bundle",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.command == "write":
        payload = write_manifest()
        print(
            f"wrote {MANIFEST_FILE.relative_to(REPO_ROOT)} "
            f"({payload['file_count']} files)"
        )
        return 0

    errors = validate_manifest()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    payload = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    print(
        f"planning bundle valid: {payload.get('file_count', len(_planning_files()))} files"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
