"""Stale CI-infra-path detection for Gate 9 repair goals.

Covers the pattern that stalled worker/run_96147146e311 (dashpro PR #39):
a repair worker burning its whole attempt budget on content edits when the
real cause is that its branch predates a workflow/lint-config fix already
on the base branch.
"""

from __future__ import annotations

import json
import unittest

from app.ci_remediation import staleness


def _runner(routes: dict[str, str | None]):
    """Fake gh runner: matches on the first two args (e.g. "pr list", "run list")."""

    def run(args: list[str]) -> str | None:
        key = " ".join(args[:2])
        return routes.get(key)

    return run


class StaleCiInfraHintTests(unittest.TestCase):
    def test_pr_base_branch_reads_open_pr(self) -> None:
        runner = _runner(
            {"pr list": json.dumps([{"baseRefName": "development"}])}
        )
        base = staleness.pr_base_branch(
            runner, repo="axon-control-ops/dashpro", head_branch="worker/run_x"
        )
        self.assertEqual("development", base)

    def test_pr_base_branch_none_without_open_pr(self) -> None:
        runner = _runner({"pr list": json.dumps([])})
        base = staleness.pr_base_branch(
            runner, repo="axon-control-ops/dashpro", head_branch="worker/run_x"
        )
        self.assertIsNone(base)

    def test_base_branch_conclusion_parses_success(self) -> None:
        runner = _runner(
            {
                "run list": json.dumps(
                    [{"conclusion": "success", "headSha": "deadbeef", "status": "completed"}]
                )
            }
        )
        health = staleness.base_branch_conclusion(
            runner,
            repo="axon-control-ops/dashpro",
            workflow_name="Database SQL Linting",
            base_branch="development",
        )
        assert health is not None
        self.assertEqual("success", health["conclusion"])
        self.assertEqual("deadbeef", health["head_sha"])

    def test_base_branch_conclusion_none_on_empty_rows(self) -> None:
        runner = _runner({"run list": json.dumps([])})
        health = staleness.base_branch_conclusion(
            runner,
            repo="axon-control-ops/dashpro",
            workflow_name="Database SQL Linting",
            base_branch="development",
        )
        self.assertIsNone(health)

    def test_drifted_ci_paths_filters_to_ci_infra_prefixes(self) -> None:
        runner = _runner(
            {
                "api repos/axon-control-ops/dashpro/compare/abc123...development": "\n".join(
                    [
                        ".github/workflows/db-lint.yml",
                        ".sqlfluff",
                        "app/screens/HomeScreen.tsx",
                        "scripts/check-migration-filenames.sh",
                    ]
                )
            }
        )
        drifted = staleness.drifted_ci_paths(
            runner,
            repo="axon-control-ops/dashpro",
            base_branch="development",
            head_sha="abc123",
        )
        self.assertEqual(
            {
                ".github/workflows/db-lint.yml",
                ".sqlfluff",
                "scripts/check-migration-filenames.sh",
            },
            set(drifted),
        )
        self.assertNotIn("app/screens/HomeScreen.tsx", drifted)

    def test_stale_ci_infra_hint_positive(self) -> None:
        def runner(args: list[str]) -> str | None:
            joined = " ".join(args)
            if joined.startswith("pr list"):
                return json.dumps([{"baseRefName": "development"}])
            if joined.startswith("run list"):
                return json.dumps(
                    [{"conclusion": "success", "headSha": "greensha", "status": "completed"}]
                )
            if joined.startswith("api repos/"):
                return ".github/workflows/db-lint.yml\n"
            return None

        hint = staleness.stale_ci_infra_hint(
            repo="axon-control-ops/dashpro",
            workflow_name="Database SQL Linting",
            head_branch="worker/run_96147146e311",
            head_sha="80fa7df",
            gh_runner=runner,
        )
        assert hint is not None
        self.assertIn("Database SQL Linting", hint)
        self.assertIn("`development`", hint)
        self.assertIn(".github/workflows/db-lint.yml", hint)
        self.assertIn("merge", hint.lower())

    def test_stale_ci_infra_hint_none_when_base_not_green(self) -> None:
        def runner(args: list[str]) -> str | None:
            joined = " ".join(args)
            if joined.startswith("pr list"):
                return json.dumps([{"baseRefName": "development"}])
            if joined.startswith("run list"):
                return json.dumps([{"conclusion": "failure", "headSha": "x", "status": "completed"}])
            return None

        hint = staleness.stale_ci_infra_hint(
            repo="axon-control-ops/dashpro",
            workflow_name="Database SQL Linting",
            head_branch="worker/run_x",
            head_sha="abc",
            gh_runner=runner,
        )
        self.assertIsNone(hint)

    def test_stale_ci_infra_hint_none_when_no_drift(self) -> None:
        def runner(args: list[str]) -> str | None:
            joined = " ".join(args)
            if joined.startswith("pr list"):
                return json.dumps([{"baseRefName": "development"}])
            if joined.startswith("run list"):
                return json.dumps(
                    [{"conclusion": "success", "headSha": "greensha", "status": "completed"}]
                )
            if joined.startswith("api repos/"):
                return "app/screens/HomeScreen.tsx\n"
            return None

        hint = staleness.stale_ci_infra_hint(
            repo="axon-control-ops/dashpro",
            workflow_name="Database SQL Linting",
            head_branch="worker/run_x",
            head_sha="abc",
            gh_runner=runner,
        )
        self.assertIsNone(hint)

    def test_stale_ci_infra_hint_none_when_base_equals_head(self) -> None:
        hint = staleness.stale_ci_infra_hint(
            repo="axon-control-ops/dashpro",
            workflow_name="Database SQL Linting",
            head_branch="development",
            head_sha="abc",
            base_branch="development",
            gh_runner=lambda args: "",
        )
        self.assertIsNone(hint)

    def test_stale_ci_infra_hint_fails_open_on_runner_exception(self) -> None:
        def boom(_args: list[str]) -> str | None:
            raise RuntimeError("gh unavailable")

        hint = staleness.stale_ci_infra_hint(
            repo="axon-control-ops/dashpro",
            workflow_name="Database SQL Linting",
            head_branch="worker/run_x",
            head_sha="abc",
            base_branch="development",
            gh_runner=boom,
        )
        self.assertIsNone(hint)

    def test_stale_ci_infra_hint_none_on_missing_inputs(self) -> None:
        self.assertIsNone(
            staleness.stale_ci_infra_hint(
                repo="",
                workflow_name="Database SQL Linting",
                head_branch="worker/run_x",
                head_sha="abc",
            )
        )


if __name__ == "__main__":
    unittest.main()
