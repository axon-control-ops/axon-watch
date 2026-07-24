"""Gate 9 CI remediation — HMAC, classify, ingest, inbox merge, report."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


def _sign(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _failure_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "action": "completed",
        "workflow_run": {
            "id": 30075110718,
            "name": "Axon-X Fast Gate",
            "status": "completed",
            "conclusion": "failure",
            "head_branch": "feat/gate9-drill",
            "head_sha": "abc123deadbeef",
            "html_url": "https://github.com/axon-control-ops/axon-watch/actions/runs/30075110718",
            "display_title": "Drill ratchet overshoot",
            "path": ".github/workflows/fast-gate.yml",
        },
        "repository": {
            "name": "axon-watch",
            "full_name": "axon-control-ops/axon-watch",
            "owner": {"login": "axon-control-ops"},
        },
        "jobs": [
            {
                "name": "fast-gate",
                "conclusion": "failure",
                "steps": [
                    {"name": "Contracts + file sizes + unit tests", "conclusion": "failure"},
                ],
            }
        ],
    }
    payload.update(overrides)
    return payload


class CiRemediationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        db_path = str(Path(self._tmpdir.name) / "cp.sqlite3")
        os.environ["AXON_WATCH_CONTROL_PLANE_DB"] = db_path
        os.environ["AXON_WATCH_GITHUB_WEBHOOK_SECRET"] = "test-webhook-secret"
        self.addCleanup(lambda: os.environ.pop("AXON_WATCH_CONTROL_PLANE_DB", None))
        self.addCleanup(lambda: os.environ.pop("AXON_WATCH_GITHUB_WEBHOOK_SECRET", None))

        from app.ci_remediation import clear_config_cache_for_tests, reset_ci_signal_store_for_tests
        from app.persistence import run_store, task_store

        clear_config_cache_for_tests()
        reset_ci_signal_store_for_tests()
        task_store.reset_store()
        run_store.reset_store()
        self.addCleanup(clear_config_cache_for_tests)
        self.addCleanup(reset_ci_signal_store_for_tests)
        self.addCleanup(task_store.reset_store)
        self.addCleanup(run_store.reset_store)

    def test_hmac_rejects_bad_signature(self) -> None:
        from app.ci_remediation.hmac_verify import verify_github_signature

        body = b'{"action":"completed"}'
        self.assertFalse(
            verify_github_signature(body=body, signature_header="sha256=deadbeef")
        )
        good = _sign("test-webhook-secret", body)
        self.assertTrue(verify_github_signature(body=body, signature_header=good))

    def test_classify_completed_failure(self) -> None:
        from app.ci_remediation.classify import classify_workflow_run_event

        classified = classify_workflow_run_event(_failure_payload())
        assert classified is not None
        self.assertEqual("axon-control-ops", classified["github_owner"])
        self.assertEqual("axon-watch", classified["github_repo"])
        self.assertEqual("Axon-X Fast Gate", classified["workflow_name"])
        self.assertIn("Contracts", classified["failing_step"])

    def test_classify_ignores_success(self) -> None:
        from app.ci_remediation.classify import classify_workflow_run_event

        payload = _failure_payload()
        run = dict(payload["workflow_run"])  # type: ignore[arg-type]
        run["conclusion"] = "success"
        payload["workflow_run"] = run
        self.assertIsNone(classify_workflow_run_event(payload))

    def test_config_matches_axon_binding(self) -> None:
        from app.ci_remediation.config import load_ci_remediation_config, match_binding

        bindings = load_ci_remediation_config(force_reload=True)
        self.assertTrue(any(b.enabled and b.workspace_id == "workspace_axon_watch" for b in bindings))
        dashpro_workflows = {
            b.workflow_name
            for b in bindings
            if b.enabled and b.workspace_id == "workspace_dashpro"
        }
        self.assertEqual(
            {
                "Android CI/CD Pipeline",
                "CI",
                "Database SQL Linting",
                "Docs Policy Enforcement",
                "Security Scan",
                "Voice Benchmark Nightly",
            },
            dashpro_workflows,
        )
        matched = match_binding(
            github_owner="axon-control-ops",
            github_repo="axon-watch",
            workflow_name="Axon-X Fast Gate",
        )
        assert matched is not None
        self.assertEqual("watcher", matched.owner_role)

    def test_ingest_creates_signal_task_and_dedupes(self) -> None:
        from app.ci_remediation.ingest import ingest_workflow_run_event
        from app.ci_remediation.report import ci_inbox_items
        from app.persistence import task_store

        with mock.patch(
            "app.ci_remediation.ingest.dispatch_repair_run",
            return_value={"run_id": "run_ci_test"},
        ):
            first = ingest_workflow_run_event(_failure_payload(), dispatch=True)
            second = ingest_workflow_run_event(_failure_payload(), dispatch=True)

        self.assertTrue(first.accepted)
        self.assertEqual("ingested", first.reason)
        self.assertTrue(first.task_id.startswith("task-"))
        self.assertTrue(second.duplicate)
        task = task_store.get_task(first.task_id)
        assert task is not None
        self.assertEqual("leased", task["status"])
        self.assertEqual("watcher", task["owner_role"])
        self.assertTrue(str(task["goal"]).startswith("CI repair:"))
        self.assertIn(first.dedupe_key, str(task["goal"]))
        items = ci_inbox_items()
        self.assertTrue(any("Fast Gate failed" in str(i.get("title")) for i in items))

    def test_inbox_projection_merges_ci_items(self) -> None:
        from app.ci_remediation.ingest import ingest_workflow_run_event
        from app.inbox_projection import build_inbox_response

        with mock.patch(
            "app.ci_remediation.ingest.dispatch_repair_run",
            return_value=None,
        ):
            ingest_workflow_run_event(_failure_payload(), dispatch=False)

        projected = build_inbox_response(
            inbox_fetcher=lambda: {"items": [], "count": 0, "updated_at": ""},
            allow_empty_unavailable=False,
        )
        titles = [str(item.get("title")) for item in projected["items"]]  # type: ignore[index]
        self.assertTrue(any("Fast Gate failed" in title for title in titles))

    def test_report_outcome_updates_signal(self) -> None:
        from app.ci_remediation.ingest import ingest_workflow_run_event
        from app.ci_remediation.report import mark_repair_outcome, spoken_report_line

        with mock.patch(
            "app.ci_remediation.ingest.dispatch_repair_run",
            return_value=None,
        ):
            result = ingest_workflow_run_event(_failure_payload(), dispatch=False)

        signal = mark_repair_outcome(
            dedupe_key=result.dedupe_key,
            workspace_id="workspace_axon_watch",
            workflow_name="Axon-X Fast Gate",
            head_branch="feat/gate9-drill",
            success=True,
            detail="Draft PR opened; Fast Gate green on repair head.",
            draft_pr_url="https://github.com/axon-control-ops/axon-watch/pull/1",
        )
        self.assertEqual("resolved", signal["status"])
        spoken = spoken_report_line(
            success=True,
            workflow_name="Axon-X Fast Gate",
            detail="Draft PR ready.",
        )
        self.assertIn("green again", spoken)

    def test_worker_prompt_includes_gate9_clause(self) -> None:
        from app.workspace_agents.config_loader import EmployeeConfig
        from app.workspace_agents.worker_prompt import build_continuous_worker_prompt

        employee = EmployeeConfig(name="Rowan", role="watcher", owns="Fast Gate")
        prompt = build_continuous_worker_prompt(
            workspace_id="workspace_axon_watch",
            employee=employee,
            task={
                "task_id": "task-ci",
                "goal": "CI repair: Axon-X Fast Gate failed on feat/x.",
                "acceptance_criteria": "green or blocker",
            },
        )
        self.assertIn("Gate 9 CI remediation", prompt)
        self.assertIn("report-outcome", prompt)

    def test_webhook_route_hmac(self) -> None:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.auth.middleware import _is_exempt
        from app.routes import github_ci_webhook

        self.assertTrue(_is_exempt("/api/webhooks/github/workflow-run"))

        app = FastAPI()
        app.include_router(github_ci_webhook.router)
        client = TestClient(app)
        body = json.dumps(_failure_payload()).encode("utf-8")
        denied = client.post(
            "/api/webhooks/github/workflow-run",
            content=body,
            headers={"Content-Type": "application/json", "X-GitHub-Event": "workflow_run"},
        )
        self.assertEqual(401, denied.status_code)

        with mock.patch(
            "app.routes.github_ci_webhook.ingest_workflow_run_event",
        ) as ingest_mock:
            from app.ci_remediation.ingest import IngestResult

            ingest_mock.return_value = IngestResult(
                accepted=True,
                reason="ingested",
                dedupe_key="ci:test",
                task_id="task-1",
                run_id="run-1",
                signal_id="signal-1",
            )
            ok = client.post(
                "/api/webhooks/github/workflow-run",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-GitHub-Event": "workflow_run",
                    "X-Hub-Signature-256": _sign("test-webhook-secret", body),
                },
            )
        self.assertEqual(200, ok.status_code)
        self.assertTrue(ok.json()["accepted"])


if __name__ == "__main__":
    unittest.main()
