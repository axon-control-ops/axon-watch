"""CLI entry for `platform reconcile` — default dry-run."""

from __future__ import annotations

import json
import sys

from app.platform_recovery.reconcile_artifacts import execute_reconcile, preview_reconcile


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    execute = "--execute" in args
    if execute:
        report = execute_reconcile()
    else:
        report = preview_reconcile()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
