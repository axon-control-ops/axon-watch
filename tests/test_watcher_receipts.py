"""Live watcher receipts surfaced to reporting agents."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.watcher_receipts import (  # noqa: E402
    RECEIPT_DIRNAME,
    load_latest_watcher_receipts,
    watcher_receipts_prompt_block,
)

NOW = datetime(2026, 8, 16, 0, 0, tzinfo=timezone.utc)


class WatcherReceiptsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="axon-watcher-receipts-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.receipts = self.root / RECEIPT_DIRNAME
        self.receipts.mkdir(parents=True, exist_ok=True)
        patcher = patch(
            "app.terminal.workspace_roots.resolve_workspace_root",
            return_value=self.root,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _write(
        self,
        filename: str,
        payload: dict,
        *,
        age_hours: float = 1.0,
    ) -> None:
        target = self.receipts / filename
        target.write_text(json.dumps(payload), encoding="utf-8")
        stamp = time.time() - (age_hours * 3600.0)
        os.utime(target, (stamp, stamp))

    def _receipt(self, agent: str, **overrides) -> dict:
        payload = {
            "agent": agent,
            "status": "ok",
            "severity": "P3",
            "summary": f"{agent} nominal",
            "run_id": (NOW - timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
        }
        payload.update(overrides)
        return payload

    def test_keeps_only_the_newest_receipt_per_agent(self) -> None:
        old = (NOW - timedelta(days=3)).isoformat().replace("+00:00", "Z")
        self._write(
            "ci-watch-2026-08-13.json",
            self._receipt("CiWatch", summary="old news", run_id=old),
            age_hours=72,
        )
        self._write(
            "ci-watch-2026-08-15.json",
            self._receipt("CiWatch", summary="fresh news"),
            age_hours=1,
        )

        receipts = load_latest_watcher_receipts("workspace_probe")
        self.assertEqual(1, len(receipts))
        self.assertEqual("fresh news", receipts[0].summary)

    def test_failing_receipts_sort_ahead_of_healthy_ones(self) -> None:
        self._write("deploy-watch.json", self._receipt("DeployWatch", status="ok"))
        self._write(
            "env-drift.json",
            self._receipt("EnvDrift", status="warn", severity="P2"),
        )
        self._write(
            "ci-watch.json",
            self._receipt("CiWatch", status="fail", severity="P1", summary="Red build"),
        )

        agents = [receipt.agent for receipt in load_latest_watcher_receipts("workspace_probe")]
        self.assertEqual(["CiWatch", "EnvDrift", "DeployWatch"], agents)

    def test_prompt_block_surfaces_failing_signal_and_source_file(self) -> None:
        self._write(
            "ci-watch-2026-08-15.json",
            self._receipt(
                "CiWatch",
                status="fail",
                severity="P1",
                summary="Red build(s) on development: CI, Security Scan.",
                needs_operator=True,
            ),
        )

        block = watcher_receipts_prompt_block("workspace_probe", now=NOW)
        self.assertIn("CiWatch: fail P1", block)
        self.assertIn("Red build(s) on development", block)
        self.assertIn("needs_operator", block)
        self.assertIn("docs/ops/agent-reports/ci-watch-2026-08-15.json", block)
        # The reason the agent could not find these itself.
        self.assertIn("NOT your isolation checkout", block)
        self.assertIn("no live signal available", block)

    def test_stale_receipts_are_labelled_not_hidden(self) -> None:
        stale_stamp = (NOW - timedelta(days=4)).isoformat().replace("+00:00", "Z")
        self._write(
            "quality-gate-2026-08-11.json",
            self._receipt(
                "QualityGate",
                status="fail",
                severity="P1",
                summary="Quality gate failed: test:ci-app.",
                run_id=stale_stamp,
            ),
            age_hours=96,
        )

        block = watcher_receipts_prompt_block("workspace_probe", now=NOW)
        self.assertIn("QualityGate", block)
        self.assertIn("STALE, not current", block)
        self.assertIn("4d ago", block)

    def test_recent_receipt_is_not_marked_stale(self) -> None:
        self._write("deploy-watch.json", self._receipt("DeployWatch"))
        block = watcher_receipts_prompt_block("workspace_probe", now=NOW)
        receipt_line = next(
            line for line in block.splitlines() if line.startswith("- DeployWatch")
        )
        self.assertIn("1h ago", receipt_line)
        self.assertNotIn("STALE", receipt_line)

    def test_empty_directory_says_watchers_did_not_report(self) -> None:
        block = watcher_receipts_prompt_block("workspace_probe", now=NOW)
        self.assertIn("none found", block)
        self.assertIn("rather than implying the services themselves are healthy", block)

    def test_missing_directory_yields_no_block(self) -> None:
        shutil.rmtree(self.receipts)
        self.assertEqual("", watcher_receipts_prompt_block("workspace_probe", now=NOW))
        self.assertEqual([], load_latest_watcher_receipts("workspace_probe"))

    def test_malformed_receipt_is_skipped_without_failing(self) -> None:
        (self.receipts / "broken.json").write_text("{not json", encoding="utf-8")
        self._write("ci-watch.json", self._receipt("CiWatch", status="fail", severity="P1"))

        receipts = load_latest_watcher_receipts("workspace_probe")
        self.assertEqual(["CiWatch"], [receipt.agent for receipt in receipts])


class WatcherReceiptsPromptWiringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="axon-watcher-prompt-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        receipts = self.root / RECEIPT_DIRNAME
        receipts.mkdir(parents=True, exist_ok=True)
        (receipts / "ci-watch.json").write_text(
            json.dumps(
                {
                    "agent": "CiWatch",
                    "status": "fail",
                    "severity": "P1",
                    "summary": "Red build(s) on development.",
                    "run_id": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                }
            ),
            encoding="utf-8",
        )
        patcher = patch(
            "app.terminal.workspace_roots.resolve_workspace_root",
            return_value=self.root,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _prompt(self, *, role: str, goal: str) -> str:
        from app.workspace_agents.config_loader import EmployeeConfig
        from app.workspace_agents.worker_prompt import build_continuous_worker_prompt

        return build_continuous_worker_prompt(
            workspace_id="workspace_probe",
            employee=EmployeeConfig(name="Probe", role=role, owns="probe"),
            task={"task_id": "task-probe", "goal": goal},
        )

    def test_lead_status_shift_receives_the_live_receipts(self) -> None:
        prompt = self._prompt(role="lead", goal="Give me the status of the app currently")
        self.assertIn("LIVE WATCHER RECEIPTS", prompt)
        self.assertIn("Red build(s) on development.", prompt)

    def test_watcher_role_receives_the_live_receipts(self) -> None:
        prompt = self._prompt(role="watcher", goal="Monitor the fleet")
        self.assertIn("LIVE WATCHER RECEIPTS", prompt)

    def test_status_goal_reaches_a_specialist_role_too(self) -> None:
        prompt = self._prompt(role="backend", goal="Report current production health")
        self.assertIn("LIVE WATCHER RECEIPTS", prompt)

    def test_ordinary_implementation_shift_is_not_padded(self) -> None:
        prompt = self._prompt(role="backend", goal="Add a lessons service unit test")
        self.assertNotIn("LIVE WATCHER RECEIPTS", prompt)


if __name__ == "__main__":
    unittest.main()
