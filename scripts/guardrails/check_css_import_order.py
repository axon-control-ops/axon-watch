#!/usr/bin/env python3
"""Fail when CSS @import appears after other statements in a file.

PostCSS/Vite requires @import to precede all other statements (besides
@charset / empty @layer). Mid-file imports surface as noisy Vite warnings
and can break CSS loading order.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSS_ROOTS = (
    ROOT / "apps/console-web/src/styles",
    ROOT / "apps/console-web/src/features",
)


def _is_skippable(stripped: str) -> bool:
    if not stripped:
        return True
    if stripped.startswith("/*") or stripped.startswith("*") or stripped.startswith("//"):
        return True
    if stripped.startswith("@charset"):
        return True
    # Empty @layer blocks are allowed before @import per the CSS cascade.
    if stripped.startswith("@layer") and "{" not in stripped:
        return True
    return False


def find_mid_file_imports(path: Path) -> list[tuple[int, str]]:
    violations: list[tuple[int, str]] = []
    saw_other_statement = False
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if _is_skippable(stripped):
            continue
        if stripped.startswith("@import"):
            if saw_other_statement:
                violations.append((index, stripped))
            continue
        saw_other_statement = True
    return violations


def iter_css_files() -> list[Path]:
    files: list[Path] = []
    for root in CSS_ROOTS:
        if not root.is_dir():
            continue
        files.extend(sorted(root.rglob("*.css")))
    return files


def main() -> int:
    failures: list[str] = []
    for path in iter_css_files():
        for line_no, statement in find_mid_file_imports(path):
            rel = path.relative_to(ROOT).as_posix()
            failures.append(f"FAIL {rel}:{line_no}: mid-file {statement}")

    if failures:
        for item in failures:
            print(item)
        print(
            "CSS @import order guardrail failed. "
            "Keep @import at the top of each file, or hoist into a parent aggregator."
        )
        return 1

    print("CSS @import order guardrail passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
