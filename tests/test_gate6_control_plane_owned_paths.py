"""Gate 6 must not fail a run for paths the control plane itself wrote.

Regression coverage for the single largest source of live fleet failures
found on 2026-08-06: 16 of 44 failed runs in a 12h window died with
"Workspace delivery blocked: missing or failing acceptance_evidence
(Gate 6)", whose underlying acceptance receipt read
`acceptance=fail · policy=out_of_scope · mode=inspect_fallback_no_contract
· paths=4`.

The "changed paths" were not agent work at all — they were Axon's own
bookkeeping written into the isolation worktree before/around the agent's
turn: `.axon-si/MARKER`, `.axon-si/baseline.json`, `.axon-si/metrics.json`
(safe-improvement instrumentation) and `.cursor/mcp.json` (written by
cli_runtime/research_mcp.py::ensure_workspace_research_mcp). Even read-only
consultative runs, which cannot write anything, failed this way.

workspace_delivery/publish.py already excluded `.axon-si/` from what it
publishes; the scope-evaluation step simply never applied the same rule.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.diff_policy import (  # noqa: E402
    is_control_plane_owned_path,
    strip_control_plane_owned_paths,
)
from app.workspace_agents.verifier_checks import evaluate_acceptance  # noqa: E402

# The exact untracked set observed in preserved isolation worktrees under
# /tmp/axon-si-run_*/checkout on the live host.
_OBSERVED_CONTROL_PLANE_PATHS = [
    ".axon-si/MARKER",
    ".axon-si/baseline.json",
    ".axon-si/metrics.json",
    ".cursor/mcp.json",
]


class ControlPlaneOwnedPathTests(unittest.TestCase):
    def test_observed_live_paths_are_all_recognized(self) -> None:
        for path in _OBSERVED_CONTROL_PLANE_PATHS:
            self.assertTrue(
                is_control_plane_owned_path(path), f"should be control-plane owned: {path}"
            )

    def test_real_agent_work_is_not_swallowed(self) -> None:
        for path in (
            "apps/console-web/src/App.vue",
            "services/control-plane/app/main.py",
            "README.md",
            ".github/workflows/fast-gate.yml",
        ):
            self.assertFalse(
                is_control_plane_owned_path(path), f"must stay in scope: {path}"
            )

    def test_other_cursor_config_stays_in_scope(self) -> None:
        # Deliberately narrow: only the MCP config we write ourselves is
        # exempt. An agent editing other Cursor config must still be policed.
        self.assertFalse(is_control_plane_owned_path(".cursor/rules.md"))
        self.assertFalse(is_control_plane_owned_path(".cursor/settings.json"))
        self.assertTrue(is_control_plane_owned_path(".cursor/mcp.json"))

    def test_leading_dot_slash_and_trailing_slash_are_normalized(self) -> None:
        self.assertTrue(is_control_plane_owned_path("./.axon-si/metrics.json"))
        self.assertTrue(is_control_plane_owned_path(".axon-si/"))
        self.assertTrue(is_control_plane_owned_path(".axon-si"))

    def test_strip_keeps_agent_paths_and_preserves_order(self) -> None:
        mixed = [
            ".axon-si/MARKER",
            "apps/console-web/src/App.vue",
            ".cursor/mcp.json",
            "README.md",
        ]
        self.assertEqual(
            ["apps/console-web/src/App.vue", "README.md"],
            strip_control_plane_owned_paths(mixed),
        )

    def test_empty_and_blank_entries_are_not_treated_as_owned(self) -> None:
        self.assertFalse(is_control_plane_owned_path(""))
        self.assertFalse(is_control_plane_owned_path("   "))


class Gate6AcceptanceWithControlPlanePathsTests(unittest.TestCase):
    """End-to-end proof against evaluate_acceptance, the function that
    actually produced the live `policy=out_of_scope` verdict."""

    CONTRACT = {
        "allowed_paths": ["apps/", "services/"],
        "forbidden_path_globs": ["**/.env"],
        "verifier": {"required_checks": []},
        "commands": {},
    }

    def test_control_plane_paths_alone_no_longer_fail_acceptance(self) -> None:
        # Before the fix this produced acceptance=fail policy=out_of_scope —
        # the exact live failure, on a run where the agent wrote nothing.
        verdict = evaluate_acceptance(
            contract=self.CONTRACT,
            check_results={},
            changed_paths=strip_control_plane_owned_paths(_OBSERVED_CONTROL_PLANE_PATHS),
        )
        self.assertTrue(verdict.passed, verdict.summary)
        self.assertEqual([], verdict.policy_findings)

    def test_genuine_out_of_scope_change_still_fails(self) -> None:
        # The guard must keep doing its real job: control-plane noise stripped,
        # but an actual out-of-scope agent write still trips out_of_scope.
        verdict = evaluate_acceptance(
            contract=self.CONTRACT,
            check_results={},
            changed_paths=strip_control_plane_owned_paths(
                [".axon-si/MARKER", "/etc/passwd_clone", "some/other/place.py"]
            ),
        )
        self.assertFalse(verdict.passed)
        self.assertTrue(any(f.code == "out_of_scope" for f in verdict.policy_findings))

    def test_in_scope_agent_work_mixed_with_control_plane_noise_passes(self) -> None:
        # task_allowed_paths is required for a *writing* task: evaluate_acceptance
        # uses fail_closed_missing_task=True, so an unscoped task denies all
        # paths. Supplying it here mirrors the real Gate 6 caller, which reads
        # allowed_paths off the task record.
        verdict = evaluate_acceptance(
            contract=self.CONTRACT,
            check_results={},
            changed_paths=strip_control_plane_owned_paths(
                [".axon-si/metrics.json", "apps/console-web/src/App.vue", ".cursor/mcp.json"]
            ),
            task_allowed_paths=["apps/console-web/"],
        )
        self.assertTrue(verdict.passed, verdict.summary)

    def test_control_plane_noise_passes_even_for_an_unscoped_task(self) -> None:
        # The live failures were unscoped consultative runs: no task
        # allowed_paths, so effective scope is deny-all. Stripping the
        # control-plane paths leaves nothing to police, which is the point —
        # the agent genuinely changed nothing.
        verdict = evaluate_acceptance(
            contract=self.CONTRACT,
            check_results={},
            changed_paths=strip_control_plane_owned_paths(_OBSERVED_CONTROL_PLANE_PATHS),
            task_allowed_paths=[],
        )
        self.assertTrue(verdict.passed, verdict.summary)


if __name__ == "__main__":
    unittest.main()
