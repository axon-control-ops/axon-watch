"""Staging rollback and measured canary gate tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.rollback_canary import (  # noqa: E402
    ReleaseArtifact,
    StagingController,
    evaluate_canary,
    requires_human_approval,
)


class RollbackCanaryTests(unittest.TestCase):
    def test_smoke_failure_auto_rolls_back(self) -> None:
        ctl = StagingController()
        ctl.register_artifact(
            ReleaseArtifact(artifact_id="art-1", digest="d1", project_id="proj")
        )
        ctl.register_artifact(
            ReleaseArtifact(artifact_id="art-2", digest="d2", project_id="proj")
        )
        ctl.deploy(deployment_id="dep-1", project_id="proj", artifact_id="art-1")
        ctl.deploy(deployment_id="dep-2", project_id="proj", artifact_id="art-2")
        dep = ctl.run_smoke("dep-2", passed=False)
        self.assertTrue(dep.rolled_back)
        self.assertEqual("art-1", ctl._active_by_project["proj"])

    def test_canary_thresholds_require_20_tasks_and_90_percent(self) -> None:
        outcomes = [{"success": True} for _ in range(18)]
        outcomes.extend([{"success": False}, {"success": False}])
        report = evaluate_canary(
            project_class="node_vue",
            outcomes=outcomes,
            rollback_drills=[True],
        )
        self.assertEqual(20, report.total)
        self.assertAlmostEqual(0.90, report.success_rate)
        self.assertTrue(report.meets_thresholds())

        under_count = evaluate_canary(
            project_class="node_vue",
            outcomes=[{"success": True}] * 19,
            rollback_drills=[True],
        )
        self.assertFalse(under_count.meets_thresholds())

        bad = evaluate_canary(
            project_class="node_vue",
            outcomes=[{"success": True, "unauthorized_effect": True}] + [{"success": True}] * 19,
            rollback_drills=[True],
        )
        self.assertFalse(bad.meets_thresholds())

    def test_human_approval_gates(self) -> None:
        self.assertTrue(requires_human_approval("production"))
        self.assertTrue(requires_human_approval("merge"))
        self.assertFalse(requires_human_approval("staging_smoke"))


if __name__ == "__main__":
    unittest.main()
