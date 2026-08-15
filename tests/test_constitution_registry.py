from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402
from app.constitution_health import (  # noqa: E402
    record_runtime_summary_health_snapshot,
    status_from_runtime_summary,
)
from app.constitution_seed import (  # noqa: E402
    backfill_adrs,
    seed_capabilities,
)
from app.persistence import run_store  # noqa: E402
from app.persistence import autonomous_attention_store  # noqa: E402
from app.persistence import constitution_registry_store as registry  # noqa: E402
from app.persistence import evidence_ref_adapters  # noqa: E402
from app.runs.service import create_run  # noqa: E402


class ConstitutionRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        autonomous_attention_store.reset_store()
        registry.reset_store()
        self.addCleanup(autonomous_attention_store.reset_store)
        self.addCleanup(registry.reset_store)

    def test_registry_counts_create_schema_on_fresh_db(self) -> None:
        counts = registry.registry_counts()

        self.assertIn("evidence_registry", counts)
        self.assertIn("mission_registry", counts)
        self.assertEqual(0, counts["evidence_registry"])

    def test_evidence_indexing_is_idempotent_and_decision_requires_evidence(self) -> None:
        first = registry.index_evidence(
            source_table="run_history",
            source_id="history/run_123:1",
            source_ref={"history_ref": "history/run_123", "sequence": 1},
            kind="run_created",
            summary="Run created",
            workspace_id="workspace_alpha",
            run_id="run_123",
            tags=["run_history"],
        )
        second = registry.index_evidence(
            source_table="run_history",
            source_id="history/run_123:1",
            source_ref={"history_ref": "history/run_123", "sequence": 1},
            kind="run_created",
            summary="Run created again",
            workspace_id="workspace_alpha",
            run_id="run_123",
            tags=["run_history", "updated"],
        )

        self.assertEqual(first["evidence_id"], second["evidence_id"])
        self.assertEqual(1, registry.registry_counts()["evidence_registry"])
        with self.assertRaises(ValueError):
            registry.record_decision(
                actor="scheduler",
                decision="dispatch",
                tier="auto_safe",
                risk="normal",
                explanation="No evidence attached yet",
            )

        decision = registry.record_decision(
            actor="scheduler",
            decision="dispatch",
            tier="auto_safe",
            risk="normal",
            explanation="Dispatch is backed by run evidence.",
            evidence_ids=[first["evidence_id"]],
            run_id="run_123",
        )

        self.assertEqual("scheduler", decision["actor"])
        self.assertEqual([first["evidence_id"]], decision["evidence_ids"])

    def test_run_history_backfill_uses_actual_history_ref_sequence_schema(self) -> None:
        run = create_run(
            workspace_id="workspace_alpha",
            mode="agent",
            summary="Backfill proof run",
        )

        indexed = evidence_ref_adapters.backfill_run_history(limit=20)

        self.assertGreaterEqual(indexed, 1)
        evidence = registry.list_evidence(source_table="run_history", limit=20)
        self.assertTrue(
            any(
                item["source_ref"].get("history_ref") == run["history_ref"]
                and isinstance(item["source_ref"].get("sequence"), int)
                and item["run_id"] == run["run_id"]
                for item in evidence
            )
        )

    def test_runtime_summary_health_snapshot_is_persisted(self) -> None:
        runtime_summary = {
            "generated_at": "2026-08-09T12:00:00Z",
            "control_plane": {"ready": True},
            "watch": {"connected": False},
            "degraded": {"active": False, "reasons": []},
        }

        self.assertEqual("watch_unavailable", status_from_runtime_summary(runtime_summary))
        snapshot = record_runtime_summary_health_snapshot(runtime_summary)

        self.assertEqual("platform", snapshot["scope"])
        self.assertEqual("watch_unavailable", snapshot["status"])
        self.assertEqual("runtime_summary", snapshot["source"])
        self.assertEqual(
            {"connected": False},
            snapshot["signals"]["watch"],
        )

    def test_autonomy_receipt_indexes_constitution_evidence_and_decision(self) -> None:
        receipt = autonomous_attention_store.append_receipt(
            kind="failed_shift",
            decision="dispatch",
            tier="auto_safe",
            risk="normal",
            title="Retry safe worker shift",
            detail="Previous worker hit a transient runtime issue.",
            workspace_id="workspace_dashpro",
            task_id="task-123",
        )

        evidence = registry.list_evidence(
            source_table="autonomy_attention_receipts",
            task_id="task-123",
        )
        self.assertEqual(1, len(evidence))
        self.assertEqual(receipt["receipt_id"], evidence[0]["source_id"])
        self.assertEqual("autonomy_attention", evidence[0]["kind"])

        decisions = registry.list_decisions(task_id="task-123")
        self.assertEqual(1, len(decisions))
        self.assertEqual("autonomous_attention", decisions[0]["actor"])
        self.assertEqual("dispatch", decisions[0]["decision"])
        self.assertEqual("CAP-034", decisions[0]["capability_id"])
        self.assertEqual([evidence[0]["evidence_id"]], decisions[0]["evidence_ids"])

        refreshed_evidence = registry.list_evidence(
            source_table="autonomy_attention_receipts",
            task_id="task-123",
        )
        self.assertEqual(decisions[0]["decision_id"], refreshed_evidence[0]["decision_id"])

    def test_lead_plan_receipt_indexes_constitution_evidence(self) -> None:
        from app.workspace_agents import lead_plan_store

        self.addCleanup(lead_plan_store.reset_store)
        lead_plan_store.reset_store()
        receipt = lead_plan_store.append_receipt(
            plan_id="lead-plan-test",
            workspace_id="workspace_dashpro",
            kind="lead_plan_persisted",
            payload={"summary": "Lead decomposed the operator mission."},
        )

        evidence = registry.list_evidence(source_table="lead_plan_receipts", limit=10)

        self.assertEqual(1, len(evidence))
        self.assertEqual(receipt["receipt_id"], evidence[0]["source_id"])
        self.assertEqual("lead_plan_persisted", evidence[0]["kind"])
        self.assertEqual("workspace_dashpro", evidence[0]["workspace_id"])
        self.assertEqual(
            {"receipt_id": receipt["receipt_id"], "plan_id": "lead-plan-test"},
            evidence[0]["source_ref"],
        )

    def test_persisted_lead_plan_creates_mission_and_links_receipt_evidence(self) -> None:
        from app.workspace_agents import lead_plan_store

        self.addCleanup(lead_plan_store.reset_store)
        lead_plan_store.reset_store()
        plan = lead_plan_store.persist_plan(
            workspace_id="workspace_dashpro",
            plan={
                "goal": "Fix autonomous worker routing",
                "mode": "parallel",
                "items": [{"title": "Route frontend tasks to Priya"}],
            },
            plan_key_to_task_id={"frontend": "task-frontend"},
        )

        mission = registry.mission_for_lead_plan(plan["plan_id"])
        self.assertIsNotNone(mission)
        assert mission is not None
        self.assertEqual("Fix autonomous worker routing", mission["title"])
        self.assertEqual("workspace_dashpro", mission["workspace_id"])
        self.assertEqual(["Complete: Route frontend tasks to Priya"], mission["success_criteria"])

        evidence = registry.list_evidence(source_table="lead_plan_receipts", limit=10)
        self.assertEqual(1, len(evidence))
        self.assertEqual(mission["mission_id"], evidence[0]["mission_id"])

    def test_seed_capabilities_uses_stable_capability_ids(self) -> None:
        seeded = seed_capabilities()

        self.assertGreaterEqual(seeded, 10)
        capabilities = registry.list_capabilities(limit=50)
        ids = {item["capability_id"] for item in capabilities}
        self.assertIn("CAP-007", ids)
        self.assertIn("CAP-034", ids)
        self.assertIn("CAP-070", ids)

        # Re-seeding updates the same rows rather than creating duplicates.
        seed_capabilities()
        ids_after = {item["capability_id"] for item in registry.list_capabilities(limit=50)}
        self.assertEqual(ids, ids_after)

    def test_backfill_adrs_reads_canonical_adr_markdown(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "ADR-009-constitution-registry.md").write_text(
                "# ADR-009: Constitution Registry\n\n## Status\n\nAccepted\n\n## Decision\n\nPersist it.",
                encoding="utf-8",
            )

            indexed = backfill_adrs(adr_root=root)

        self.assertEqual(1, indexed)
        adrs = registry.list_adrs()
        self.assertEqual(1, len(adrs))
        self.assertEqual(9, adrs[0]["number"])
        self.assertEqual("ADR-009: Constitution Registry", adrs[0]["title"])
        self.assertEqual("accepted", adrs[0]["status"])


class ConstitutionRegistryRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        registry.reset_store()
        self.addCleanup(registry.reset_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_constitution_routes_expose_registry_records(self) -> None:
        overview = self.client.get("/api/operator/constitution")
        self.assertEqual(200, overview.status_code)
        self.assertIn("evidence_registry", overview.json()["registries"])

        mission = self.client.post(
            "/api/operator/constitution/missions",
            json={
                "title": "Close constitution registry gap",
                "workspace_id": "workspace_axon_watch",
                "success_criteria": ["Registries persist", "Read APIs work"],
            },
        )
        self.assertEqual(200, mission.status_code)

        missions = self.client.get(
            "/api/operator/constitution/missions",
            params={"workspace_id": "workspace_axon_watch"},
        )
        self.assertEqual(200, missions.status_code)
        self.assertEqual(1, missions.json()["count"])
        self.assertEqual(
            "Close constitution registry gap",
            missions.json()["items"][0]["title"],
        )

        capability = self.client.post(
            "/api/operator/constitution/capabilities",
            json={
                "name": "CAP-007 Evidence Engine",
                "description": "Indexes execution evidence without duplicating execution.",
                "route_paths": ["/api/operator/constitution/evidence"],
            },
        )
        self.assertEqual(200, capability.status_code)

        capabilities = self.client.get("/api/operator/constitution/capabilities")
        self.assertEqual(200, capabilities.status_code)
        self.assertEqual(1, capabilities.json()["count"])

        adr = self.client.post(
            "/api/operator/constitution/adrs",
            json={
                "number": 9,
                "title": "Constitution registry spine",
                "status": "accepted",
                "capability_ids": [capability.json()["capability_id"]],
            },
        )
        self.assertEqual(200, adr.status_code)

        adrs = self.client.get("/api/operator/constitution/adrs")
        self.assertEqual(200, adrs.status_code)
        self.assertEqual(1, adrs.json()["count"])

        debt = self.client.post(
            "/api/operator/constitution/debt",
            json={
                "title": "Wire scheduler decisions into decision registry",
                "severity": "medium",
                "area": "autonomy",
            },
        )
        self.assertEqual(200, debt.status_code)

        debts = self.client.get("/api/operator/constitution/debt")
        self.assertEqual(200, debts.status_code)
        self.assertEqual(1, debts.json()["count"])

    def test_health_capture_endpoint_records_runtime_summary_snapshot(self) -> None:
        from unittest.mock import patch

        with patch(
            "app.runtime_summary_assembler.assemble_runtime_summary",
            return_value={
                "generated_at": "2026-08-09T12:01:00Z",
                "control_plane": {"ready": True},
                "watch": {"connected": True},
                "degraded": {"active": False, "reasons": []},
            },
        ):
            response = self.client.post(
                "/api/operator/constitution/health/capture-runtime-summary"
            )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("ready", payload["snapshot"]["status"])
        self.assertEqual("runtime_summary_light", payload["snapshot"]["source"])

        snapshots = self.client.get("/api/operator/constitution/health")
        self.assertEqual(200, snapshots.status_code)
        self.assertEqual(1, snapshots.json()["count"])

    def test_seed_endpoint_indexes_capabilities_and_canonical_adrs(self) -> None:
        response = self.client.post("/api/operator/constitution/seed")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertGreaterEqual(payload["results"]["capabilities"], 10)
        self.assertGreaterEqual(payload["results"]["adrs"], 1)

        capabilities = self.client.get("/api/operator/constitution/capabilities")
        ids = {item["capability_id"] for item in capabilities.json()["items"]}
        self.assertIn("CAP-034", ids)

        adrs = self.client.get("/api/operator/constitution/adrs")
        self.assertGreaterEqual(adrs.json()["count"], 1)


if __name__ == "__main__":
    unittest.main()
