#!/usr/bin/env python3
"""Push the canonical planning bundle to axon-local continuity mirror."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PLANNING_DIR = REPO_ROOT / "docs" / "planning"
DEFAULT_MIRROR = Path("/home/edp/axon-nvme/repos/axon-local/Plans/Axon-Watch")


def sync_mirror(target_dir: Path, *, dry_run: bool) -> list[str]:
    if not PLANNING_DIR.is_dir():
        return [f"missing canonical planning dir: {PLANNING_DIR}"]

    target_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []

    for source in sorted(PLANNING_DIR.iterdir()):
        if not source.is_file():
            continue
        if source.name == "MANIFEST.json":
            continue
        destination = target_dir / source.name
        if dry_run:
            copied.append(source.name)
            continue
        shutil.copy2(source, destination)
        copied.append(source.name)

    return copied


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        type=Path,
        default=DEFAULT_MIRROR,
        help="axon-local mirror directory",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    copied = sync_mirror(args.target, dry_run=args.dry_run)
    if isinstance(copied, list) and copied and isinstance(copied[0], str) and copied[0].startswith("missing"):
        print(f"ERROR: {copied[0]}", file=sys.stderr)
        return 1

    action = "would copy" if args.dry_run else "copied"
    print(f"{action} {len(copied)} files to {args.target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
