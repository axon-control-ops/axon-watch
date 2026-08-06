"""Autonomy guardrails: task scope, file-size patrol, company work sources."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import run_store, task_store  # noqa: E402
from app.workspace_agents.diff_policy import (  # noqa: E402
    evaluate_changed_paths,
    resolve_effective_allowed_paths,
)
from app.workspace_agents.file_size_patrol import (  # noqa: E402
    FileSizePatrolFinding,
    MANIFEST_REL,
    classify_file_size_findings,
    enqueue_file_size_patrol_tasks,
    propose_manifest_lowering,
)
from app.workspace_agents.verifier_checks import evaluate_acceptance  # noqa: E402
from app.workspace_agents.company_work_sources import (  # noqa: E402
    list_enabled_work_sources,
    run_scheduled_work_sources,
)


class EffectiveScopeTests(unittest.TestCase):
    def test_missing_task_scope_falls_back_to_contract(self) -> None:
        self.assertEqual(
            ["apps/", "services/"],
            resolve_effective_allowed_paths(
                contract_allowed_paths=["apps/", "services/"],
                task_allowed_paths=[],
            ),
        )

    def test_missing_task_scope_can_fail_closed_at_execution_boundary(self) -> None:
        self.assertEqual(
            ["__axon_deny_all__"],
            resolve_effective_allowed_paths(
                contract_allowed_paths=["apps/", "services/"],
                task_allowed_paths=[],
                fail_closed_missing_task=True,
            ),
        )

    def test_task_scope_intersects_contract(self) -> None:
        effective = resolve_effective_allowed_paths(
            contract_allowed_paths=["apps/", "services/", "scripts/"],
            task_allowed_paths=["scripts/guardrails/", "docs/"],
        )
        self.assertEqual(["scripts/guardrails/"], effective)
        findings = evaluate_changed_paths(
            ["scripts/guardrails/hotspot_budgets.json", "apps/console-web/src/App.vue"],
            allowed_paths=effective,
            forbidden_path_globs=["**/.env"],
        )
        codes = {(f.code, f.path) for f in findings}
        self.assertIn(("out_of_scope", "apps/console-web/src/App.vue"), codes)

    def test_disjoint_scopes_deny_all_paths(self) -> None:
        effective = resolve_effective_allowed_paths(
            contract_allowed_paths=["apps/"],
            task_allowed_paths=["docs/"],
        )
        self.assertEqual(["__axon_deny_all__"], effective)
        findings = evaluate_changed_paths(
            ["apps/console-web/src/App.vue", "docs/README.md"],
            allowed_paths=effective,
            forbidden_path_globs=[],
        )
        codes = {f.code for f in findings}
        self.assertIn("out_of_scope", codes)

    def test_evaluate_acceptance_uses_task_allowed_paths(self) -> None:
        contract = {
            "allowed_paths": ["apps/", "scripts/"],
            "forbidden_path_globs": ["**/.env"],
            "verifier": {"required_checks": []},
            "commands": {},
        }
        blocked = evaluate_acceptance(
            contract=contract,
            check_results={},
            changed_paths=["apps/console-web/src/App.vue"],
            task_allowed_paths=["scripts/guardrails/"],
        )
        self.assertFalse(blocked.passed)
        self.assertTrue(
            any(f.code == "out_of_scope" for f in blocked.policy_findings)
        )
        passed = evaluate_acceptance(
            contract=contract,
            check_results={},
            changed_paths=["scripts/guardrails/hotspot_budgets.json"],
            task_allowed_paths=["scripts/guardrails/"],
        )
        self.assertTrue(passed.passed)


class FileSizePatrolTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        task_store.reset_store()
        self.addCleanup(task_store.reset_store)

    def test_propose_manifest_lowering_never_raises(self) -> None:
        manifest = {
            "critical_hotspots": {},
            "ratcheted_oversize_files": {
                "apps/big.py": {"max_lines": 900, "note": "temp"},
            },
        }
        lowered = propose_manifest_lowering(
            manifest,
            path="apps/big.py",
            suggested_max_lines=820,
        )
        assert lowered is not None
        self.assertEqual(
            820,
            lowered["ratcheted_oversize_files"]["apps/big.py"]["max_lines"],
        )
        self.assertIsNone(
            propose_manifest_lowering(
                manifest,
                path="apps/big.py",
                suggested_max_lines=950,
            )
        )

    def test_enqueue_prefers_stale_manifest_with_explicit_paths(self) -> None:
        findings = [
            FileSizePatrolFinding(
                kind="extraction",
                path="apps/huge.vue",
                lines=900,
                budget=500,
                detail="needs extract",
            ),
            FileSizePatrolFinding(
                kind="stale_manifest",
                path="apps/ok.py",
                lines=400,
                budget=520,
                suggested_max_lines=400,
                detail="lower manifest",
            ),
        ]
        created = enqueue_file_size_patrol_tasks(
            workspace_id="workspace_axon_watch",
            findings=findings,
            max_new_tasks=1,
        )
        self.assertEqual(1, len(created))
        self.assertIn("lower stale ratchet", created[0]["goal"])
        self.assertEqual([MANIFEST_REL], created[0]["allowed_paths"])
        self.assertEqual("low", created[0]["risk"])

    def test_classify_runs_against_real_repo(self) -> None:
        findings = classify_file_size_findings(REPO_ROOT)
        self.assertIsInstance(findings, list)
        for item in findings:
            self.assertIn(item.kind, {"stale_manifest", "extraction"})


class CompanyWorkSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        task_store.reset_store()
        self.addCleanup(task_store.reset_store)

    def test_config_lists_ci_and_file_size_sources(self) -> None:
        sources = list_enabled_work_sources(REPO_ROOT)
        ids = {str(item.get("id")) for item in sources}
        self.assertIn("ci_remediation", ids)
        self.assertIn("file_size_patrol", ids)
        self.assertIn("lead_team_checkin", ids)
        self.assertIn("ci_stale_signal_sweep", ids)
        self.assertIn("fleet_self_heal_detect", ids)

    def test_run_scheduled_work_sources_dispatches_fleet_self_heal_detect(self) -> None:
        with patch(
            "app.workspace_agents.company_work_sources.list_runs", return_value=[]
        ), patch(
            "app.workspace_agents.file_size_patrol.classify_file_size_findings", return_value=[]
        ), patch(
            "app.workspace_agents.lead_team_checkin.run_lead_team_checkin",
            return_value={"work_source": "lead_team_checkin", "created_tasks": []},
        ), patch(
            "app.ci_remediation.stale_sweep.sweep_stale_ci_signals",
            return_value={"work_source": "ci_stale_signal_sweep", "resolved_count": 0},
        ), patch(
            "app.fleet_self_heal.detect.scan_fleet_failures"
        ) as scan_mock:
            from app.fleet_self_heal.detect import DetectScanResult

            scan_mock.return_value = DetectScanResult(
                scanned_runs=3, fleet_infra_observations=1,
                dispatchable_fingerprints=[], regressed_fingerprints=[],
                skipped_min_interval=False,
            )
            result = run_scheduled_work_sources(root=REPO_ROOT)
        source_result = result["sources"]["fleet_self_heal_detect"]
        self.assertEqual(3, source_result["scanned_runs"])
        self.assertEqual(1, source_result["fleet_infra_observations"])
        scan_mock.assert_called_once_with(window_hours=6.0, min_interval_seconds=300.0)

    def test_run_scheduled_work_sources_recovers_orphans(self) -> None:
        created = task_store.create_task(
            workspace_id="workspace_axon_watch",
            goal="CI repair: Axon-X Fast Gate failed on feat/orphan",
            owner_role="watcher",
        )
        task_store.lease_task(
            created["task_id"],
            lease_holder="ci-remediation",
            run_id="run_dead",
        )
        with patch(
            "app.workspace_agents.company_work_sources.list_runs",
            return_value=[{"run_id": "run_dead", "phase": "cancelled"}],
        ), patch(
            "app.workspace_agents.file_size_patrol.classify_file_size_findings",
            return_value=[],
        ), patch(
            "app.workspace_agents.lead_team_checkin.run_lead_team_checkin",
            return_value={"work_source": "lead_team_checkin", "created_tasks": []},
        ), patch(
            "app.ci_remediation.stale_sweep.sweep_stale_ci_signals",
            return_value={"work_source": "ci_stale_signal_sweep", "resolved_count": 0},
        ):
            result = run_scheduled_work_sources(root=REPO_ROOT)
        self.assertEqual(1, len(result["recovered_leases"]))
        again = task_store.get_task(created["task_id"])
        assert again is not None
        self.assertEqual("open", again["status"])


class CiRemediationSupersedeTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        task_store.reset_store()
        self.addCleanup(task_store.reset_store)

    def test_newer_repair_cancels_prior_open_tasks(self) -> None:
        from app.ci_remediation.config import CiRemediationBinding
        from app.ci_remediation.dispatch_repair import create_and_lease_repair_task

        old = task_store.create_task(
            workspace_id="workspace_axon_watch",
            goal="CI repair: Axon-X Fast Gate failed on feat/gate9. Old head.",
            owner_role="watcher",
        )
        binding = CiRemediationBinding(
            enabled=True,
            workspace_id="workspace_axon_watch",
            github_owner="axon-control-ops",
            github_repo="axon-watch",
            workflow_name="Axon-X Fast Gate",
            attempt_budget=3,
            push_policy="draft_pr",
            owner_role="watcher",
            escalate_role="integrations",
            lead_role="lead",
            dispatch_on_ingest=False,
        )
        leased = create_and_lease_repair_task(
            binding=binding,
            classified={
                "workflow_name": "Axon-X Fast Gate",
                "head_branch": "feat/gate9",
                "head_sha": "abc123",
                "run_id": "99",
                "html_url": "https://example.test/99",
                "failing_step": "file-size",
            },
            dedupe_key="owner/repo:Axon-X Fast Gate:feat/gate9:abc123",
        )
        prior = task_store.get_task(old["task_id"])
        assert prior is not None
        self.assertEqual("cancelled", prior["status"])
        self.assertIn("superseded", str(prior.get("terminal_outcome") or "").lower())
        self.assertEqual("leased", leased["status"])


class PublishScopeParityTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        task_store.reset_store()
        self.addCleanup(task_store.reset_store)

    def test_publish_scope_blocks_out_of_task_paths(self) -> None:
        from app.workspace_delivery import publish as publish_mod

        created = task_store.create_task(
            workspace_id="workspace_axon_watch",
            goal="File-size patrol: lower stale ratchet",
            allowed_paths=[MANIFEST_REL],
            owner_role="watcher",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "app.workspace_agents.verifier_checks.load_repo_contract",
                return_value={
                    "allowed_paths": ["apps/", "scripts/"],
                    "forbidden_path_globs": ["**/.env"],
                },
            ):
                hit = publish_mod._scan_publish_scope(
                    root,
                    ["apps/console-web/src/App.vue"],
                    task_id=created["task_id"],
                )
                ok = publish_mod._scan_publish_scope(
                    root,
                    [MANIFEST_REL],
                    task_id=created["task_id"],
                )
        self.assertIsNotNone(hit)
        assert hit is not None
        self.assertIn("out_of_scope", hit)
        self.assertIsNone(ok)


if __name__ == "__main__":
    unittest.main()
