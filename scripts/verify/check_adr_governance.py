from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.verify.common import CheckResult, REPO_ROOT, emit_many, load_config


ADR_PATTERN = re.compile(r"ADR-(\d{3})-[a-z0-9-]+\.md$")
SUPERSEDED_REFERENCE = re.compile(r"Superseded by ADR-\d{3}\b")


def _extract_headings(text: str) -> list[str]:
    headings: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            headings.append(line[3:].strip())
    return headings


def _extract_status(text: str) -> str | None:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() == "## Status":
            for candidate in lines[index + 1 :]:
                stripped = candidate.strip()
                if not stripped:
                    continue
                if stripped.startswith("#"):
                    return None
                return stripped
    return None


def _check_scaffold(adr_dir: Path) -> list[CheckResult]:
    results: list[CheckResult] = []
    template_path = adr_dir / "_TEMPLATE.md"
    readme_path = adr_dir / "README.md"

    results.append(
        CheckResult(
            name="adr_template",
            status="pass" if template_path.exists() else "fail",
            message="template present" if template_path.exists() else "missing docs/adr/_TEMPLATE.md",
        )
    )
    results.append(
        CheckResult(
            name="adr_process_readme",
            status="pass" if readme_path.exists() else "fail",
            message="process readme present" if readme_path.exists() else "missing docs/adr/README.md",
        )
    )
    return results


def _check_numbered_adrs(
    adr_dir: Path,
    statuses: list[str],
    required_sections: list[str],
    strict_pending: bool,
) -> list[CheckResult]:
    adr_files = sorted(path for path in adr_dir.glob("ADR-*.md") if ADR_PATTERN.match(path.name))
    if not adr_files:
        status = "fail" if strict_pending else "pending"
        return [
            CheckResult(
                name="adr_numbered_records",
                status=status,
                message="no numbered ADRs exist yet",
                details=["governance scaffold is ready for the first accepted or proposed ADR"],
            )
        ]

    results: list[CheckResult] = []
    numbers = [int(ADR_PATTERN.match(path.name).group(1)) for path in adr_files if ADR_PATTERN.match(path.name)]
    expected = list(range(1, len(numbers) + 1))
    if numbers == expected:
        results.append(
            CheckResult(
                name="adr_numbering_sequence",
                status="pass",
                message=f"ADR numbers are sequential from {numbers[0]:03d} to {numbers[-1]:03d}",
            )
        )
    else:
        results.append(
            CheckResult(
                name="adr_numbering_sequence",
                status="fail",
                message=f"ADR numbering is not sequential: found {numbers}",
            )
        )

    for adr_file in adr_files:
        text = adr_file.read_text(encoding="utf-8")
        headings = _extract_headings(text)
        missing_sections = [section for section in required_sections if section not in headings]
        if missing_sections:
            results.append(
                CheckResult(
                    name=f"{adr_file.name}_sections",
                    status="fail",
                    message="missing required ADR sections",
                    details=missing_sections,
                )
            )
            continue

        status_value = _extract_status(text)
        if status_value not in statuses:
            results.append(
                CheckResult(
                    name=f"{adr_file.name}_status",
                    status="fail",
                    message=f"invalid ADR status: {status_value!r}",
                    details=[f"allowed statuses: {', '.join(statuses)}"],
                )
            )
            continue

        if status_value == "Superseded" and not SUPERSEDED_REFERENCE.search(text):
            results.append(
                CheckResult(
                    name=f"{adr_file.name}_supersession",
                    status="fail",
                    message="superseded ADR must reference the replacing ADR",
                )
            )
            continue

        results.append(
            CheckResult(
                name=f"{adr_file.name}_governance",
                status="pass",
                message="required ADR governance structure is present",
            )
        )

    return results


def run_check(adr_dir: Path | None = None, strict_pending: bool = False) -> list[CheckResult]:
    config = load_config()["adr"]
    effective_dir = adr_dir or (REPO_ROOT / "docs" / "adr")
    results = _check_scaffold(effective_dir)
    results.extend(
        _check_numbered_adrs(
            effective_dir,
            statuses=[str(status) for status in config["statuses"]],
            required_sections=[str(section) for section in config["required_sections"]],
            strict_pending=strict_pending,
        )
    )
    return results


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Axon-Watch ADR governance scaffold.")
    parser.add_argument("--strict-pending", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    return emit_many(run_check(strict_pending=args.strict_pending))


if __name__ == "__main__":
    raise SystemExit(main())
