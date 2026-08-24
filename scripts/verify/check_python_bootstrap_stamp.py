#!/usr/bin/env python3
"""Verify the Python bootstrap stamp stays out of output/."""

from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "dev" / "ensure-python-deps.sh"
GITIGNORE_PATH = REPO_ROOT / ".gitignore"

EXPECTED_STAMP_DIR = '${repo_root}/scripts/.cache/python-bootstrap'
LEGACY_STAMP_DIR = '${repo_root}/output/python-bootstrap'
EXPECTED_GITIGNORE_LINE = "scripts/.cache/"


def require(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def main() -> int:
    script_text = SCRIPT_PATH.read_text(encoding="utf-8")
    gitignore_text = GITIGNORE_PATH.read_text(encoding="utf-8")

    require(EXPECTED_STAMP_DIR in script_text, "new stamp dir missing from ensure-python-deps.sh")
    require(LEGACY_STAMP_DIR in script_text, "legacy stamp migration missing from ensure-python-deps.sh")
    require('mv "${legacy_stamp_path}" "${stamp_path}"' in script_text, "legacy stamp migration step missing")
    require(EXPECTED_GITIGNORE_LINE in gitignore_text, ".gitignore missing scripts/.cache/ ignore")

    print("PASS: python bootstrap stamp stays outside output/ and scripts/.cache/ is ignored")
    return 0


if __name__ == "__main__":
    sys.exit(main())
