"""TEST-2 live acceptance for cross-workspace handoff records and target summaries.

Requires `./scripts/dev/up.sh` (ports 4173 / 8787 / 8788).

Run:
  python3 -m unittest tests.test_test2_workspace_handoff_acceptance
  ./scripts/verify/test2-workspace-handoff.sh
"""

from __future__ import annotations

import json
import os
import unittest
import urllib.error
import urllib.request

SOURCE_WORKSPACE_ID = "workspace_smoke"
TARGET_WORKSPACE_ID = "workspace_axon_local"
CONTROL_PLANE_BASE = os.environ.get(
    "AXON_WATCH_CONTROL_PLANE_BASE",
    "http://127.0.0.1:8787",
)


def _request(method: str, url: str, body: dict | None = None) -> tuple[int, dict | list | str]:
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"} if body is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            raw = response.read().decode()
            if not raw:
                return response.status, {}
            try:
                return response.status, json.loads(raw)
            except json.JSONDecodeError:
                return response.status, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw


def _stack_available() -> bool:
    status, _ = _request("GET", f"{CONTROL_PLANE_BASE}/api/health")
    return status == 200


@unittest.skipUnless(_stack_available(), "dev stack not running on control-plane base URL")
class Test2WorkspaceHandoffAcceptance(unittest.TestCase):
    def test_create_handoff_from_smoke_to_axon_local(self) -> None:
        status, payload = _request(
            "POST",
            f"{CONTROL_PLANE_BASE}/api/workspaces/{SOURCE_WORKSPACE_ID}/handoffs",
            {
                "target_workspace_id": TARGET_WORKSPACE_ID,
                "task": "Verify cross-workspace handoff summary for axon-local",
                "reason": "TEST-2 acceptance",
            },
        )
        self.assertEqual(200, status)
        self.assertIsInstance(payload, dict)

        handoff = payload.get("handoff")
        self.assertIsInstance(handoff, dict)
        assert isinstance(handoff, dict)
        self.assertEqual(SOURCE_WORKSPACE_ID, handoff.get("source_workspace_id"))
        self.assertEqual(TARGET_WORKSPACE_ID, handoff.get("target_workspace_id"))
        self.assertEqual("recorded", handoff.get("status"))
        self.assertTrue(str(handoff.get("handoff_id", "")).startswith("handoff-"))

        summary = payload.get("target_workspace_summary")
        self.assertIsInstance(summary, dict)
        assert isinstance(summary, dict)
        self.assertEqual(TARGET_WORKSPACE_ID, summary.get("workspace_id"))
        self.assertEqual("project_path", summary.get("connection_kind"))
        self.assertTrue(str(summary.get("project_root", "")).endswith("axon-local"))
        self.assertIn("run_count", summary)
        self.assertIn("active_run_count", summary)
        self.assertIn("active_runs", summary)

        list_status, list_payload = _request(
            "GET",
            f"{CONTROL_PLANE_BASE}/api/workspaces/{SOURCE_WORKSPACE_ID}/handoffs",
        )
        self.assertEqual(200, list_status)
        items = list_payload.get("items") if isinstance(list_payload, dict) else []
        self.assertIsInstance(items, list)
        self.assertTrue(any(item.get("handoff_id") == handoff.get("handoff_id") for item in items))


if __name__ == "__main__":
    unittest.main()
