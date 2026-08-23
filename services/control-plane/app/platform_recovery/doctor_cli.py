"""CLI entry for `platform doctor`."""

from __future__ import annotations

import json
import sys

from app.platform_recovery.doctor import run_doctor


def main() -> int:
    report = run_doctor()
    print(json.dumps(report, indent=2, sort_keys=True))
    status = str(report.get("status") or "FAIL")
    if status == "FAIL":
        return 2
    if status in {"WARN", "BLOCKED"}:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
