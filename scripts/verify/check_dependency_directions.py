from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.verify.common import CheckResult, REPO_ROOT, emit_many, load_config


SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".vue", ".mjs", ".cjs"}


def _iter_source_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if path.is_file() and path.suffix in SOURCE_SUFFIXES:
            yield path


def _scan_rule(rule: dict[str, object], repo_root: Path, strict_pending: bool) -> CheckResult:
    source_root = repo_root / str(rule["source_root"])
    forbidden_tokens = [str(token) for token in rule["forbidden_tokens"]]

    if not source_root.exists():
        status = "fail" if strict_pending else "pending"
        return CheckResult(
            name=str(rule["name"]),
            status=status,
            message=f"source root missing: {source_root.relative_to(repo_root)}",
            details=["future slices must create this bounded source area before strict CI gating"],
        )

    source_files = list(_iter_source_files(source_root))
    if not source_files:
        status = "fail" if strict_pending else "pending"
        return CheckResult(
            name=str(rule["name"]),
            status=status,
            message=f"no source files yet under {source_root.relative_to(repo_root)}",
            details=["dependency direction scan is scaffolded but awaiting thin-slice code"],
        )

    matches: list[str] = []
    for source_file in source_files:
        text = source_file.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            for token in forbidden_tokens:
                if token in line:
                    relative = source_file.relative_to(repo_root)
                    matches.append(f"{relative}:{line_number} contains {token!r}")

    if matches:
        return CheckResult(
            name=str(rule["name"]),
            status="fail",
            message="forbidden dependency direction detected",
            details=matches[:10],
        )

    return CheckResult(
        name=str(rule["name"]),
        status="pass",
        message=f"scanned {len(source_files)} files with no forbidden dependency tokens",
        details=[f"source_root={source_root.relative_to(repo_root)}"],
    )


def run_check(repo_root: Path | None = None, strict_pending: bool = False) -> list[CheckResult]:
    config = load_config()
    effective_root = repo_root or REPO_ROOT
    return [
        _scan_rule(rule, repo_root=effective_root, strict_pending=strict_pending)
        for rule in config["dependency_rules"]
    ]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check Axon-Watch dependency direction placeholder rules."
    )
    parser.add_argument("--strict-pending", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    return emit_many(run_check(strict_pending=args.strict_pending))


if __name__ == "__main__":
    raise SystemExit(main())
