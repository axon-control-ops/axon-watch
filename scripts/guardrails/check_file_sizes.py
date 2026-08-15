#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.guardrails.common import (  # noqa: E402
    DEFAULT_LIMITS,
    evaluate_ratcheted_file,
    line_count,
    load_budget_manifest,
    ratcheted_entries,
    tracked_source_files,
)


def main() -> int:
    failed = False
    try:
        manifest = load_budget_manifest()
    except ValueError as exc:
        print(f"FAIL {exc}")
        print("File-size guardrails failed.")
        return 1

    ratchets = ratcheted_entries(manifest)
    advisory_hits: list[str] = []

    for path in tracked_source_files():
        rel = path.relative_to(ROOT).as_posix()
        lines = line_count(path)
        ratchet = ratchets.get(rel)
        if ratchet:
            error = evaluate_ratcheted_file(rel, lines, int(ratchet["max_lines"]))
            if error:
                print(error)
                failed = True
            continue

        limits = DEFAULT_LIMITS[path.suffix.lower()]
        hard_limit = limits["hard"]
        advisory_limit = limits["soft"]
        if lines > hard_limit:
            print(
                f"FAIL {rel}: {lines} lines exceeds hard limit {hard_limit}; "
                f"extract it or add a ratchet entry before merging"
            )
            failed = True
        elif lines > advisory_limit:
            advisory_hits.append(
                f"WARN {rel}: {lines} lines exceeds advisory limit {advisory_limit}"
            )

    verbose = os.environ.get("AXON_GUARDRAIL_VERBOSE", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    visible_advisories = advisory_hits if verbose else advisory_hits[:5]
    for warning in visible_advisories:
        print(warning)
    hidden_count = len(advisory_hits) - len(visible_advisories)
    if hidden_count:
        print(
            f"WARN {hidden_count} additional legacy advisory-size files omitted; "
            "set AXON_GUARDRAIL_VERBOSE=1 for the full list"
        )

    if failed:
        print("File-size guardrails failed.")
        return 1

    print("File-size guardrails passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
