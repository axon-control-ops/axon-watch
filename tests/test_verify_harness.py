from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify.check_adr_governance import run_check as run_adr_check
from scripts.verify.check_dependency_directions import run_check as run_dependency_check
from scripts.verify.check_dto_sizes import run_check as run_dto_size_check
from scripts.verify.check_latency_budget import run_check as run_latency_check


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class VerificationHarnessTests(unittest.TestCase):
    def test_runtime_latency_budget_passes_with_valid_samples(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            samples_path = Path(tmpdir) / "runtime-latency.json"
            _write_json(samples_path, {"samples_ms": [120, 150, 180, 210, 240, 260]})

            result = run_latency_check(
                "runtime_summary_latency",
                samples_file=samples_path,
                strict_pending=True,
            )

            self.assertEqual("pass", result.status)

    def test_watch_latency_budget_fails_when_threshold_exceeded(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            samples_path = Path(tmpdir) / "watch-latency.json"
            _write_json(samples_path, {"samples_ms": [100, 150, 180, 220, 240, 260]})

            result = run_latency_check(
                "watch_summary_latency",
                samples_file=samples_path,
                strict_pending=True,
            )

            self.assertEqual("fail", result.status)

    def test_dto_size_checks_use_thresholds(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_path = Path(tmpdir) / "runtime-summary.json"
            watch_path = Path(tmpdir) / "watch-summary.json"
            _write_json(runtime_path, {"summary": "x" * 64})
            _write_json(watch_path, {"summary": "y" * 64})

            results = run_dto_size_check(
                runtime_payload=runtime_path,
                watch_payload=watch_path,
                strict_pending=True,
            )

            self.assertEqual(["pass", "pass"], [result.status for result in results])

    def test_dependency_direction_check_detects_forbidden_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            source_file = repo_root / "services" / "axon-watch" / "app" / "worker.py"
            source_file.parent.mkdir(parents=True, exist_ok=True)
            source_file.write_text(
                "from apps.console_web.shell import start_shell\n",
                encoding="utf-8",
            )

            results = run_dependency_check(repo_root=repo_root, strict_pending=True)
            matched = {result.name: result.status for result in results}

            self.assertEqual("fail", matched["watch-no-ui-dependency"])

    def test_dependency_direction_check_marks_missing_roots_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            results = run_dependency_check(repo_root=Path(tmpdir), strict_pending=False)
            self.assertTrue(all(result.status == "pending" for result in results))

    def test_adr_governance_scaffold_passes_with_one_numbered_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            adr_dir = Path(tmpdir) / "docs" / "adr"
            adr_dir.mkdir(parents=True, exist_ok=True)
            (adr_dir / "README.md").write_text("# ADR Process\n", encoding="utf-8")
            (adr_dir / "_TEMPLATE.md").write_text("# ADR Template\n", encoding="utf-8")
            (adr_dir / "ADR-001-example.md").write_text(
                "\n".join(
                    [
                        "# ADR-001-example",
                        "",
                        "## Status",
                        "",
                        "Proposed",
                        "",
                        "## Context",
                        "",
                        "Need a decision.",
                        "",
                        "## Decision",
                        "",
                        "Use a bounded service.",
                        "",
                        "## Alternatives Considered",
                        "",
                        "Keep it monolithic.",
                        "",
                        "## Trade-Offs",
                        "",
                        "Smaller modules, more seams.",
                        "",
                        "## Consequences",
                        "",
                        "More explicit boundaries.",
                        "",
                        "## Reevaluation Triggers",
                        "",
                        "Persistent delivery friction.",
                    ]
                ),
                encoding="utf-8",
            )

            results = run_adr_check(adr_dir=adr_dir, strict_pending=True)
            statuses = {result.name: result.status for result in results}

            self.assertEqual("pass", statuses["adr_template"])
            self.assertEqual("pass", statuses["adr_process_readme"])
            self.assertEqual("pass", statuses["adr_numbering_sequence"])
            self.assertEqual("pass", statuses["ADR-001-example.md_governance"])

    def test_adr_governance_marks_absent_numbered_adrs_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            adr_dir = Path(tmpdir) / "docs" / "adr"
            adr_dir.mkdir(parents=True, exist_ok=True)
            (adr_dir / "README.md").write_text("# ADR Process\n", encoding="utf-8")
            (adr_dir / "_TEMPLATE.md").write_text("# ADR Template\n", encoding="utf-8")

            results = run_adr_check(adr_dir=adr_dir, strict_pending=False)
            statuses = {result.name: result.status for result in results}

            self.assertEqual("pending", statuses["adr_numbered_records"])


if __name__ == "__main__":
    unittest.main()
