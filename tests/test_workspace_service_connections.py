from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.execution_policy import role_execution_policy  # noqa: E402
from app.workspace_agents.execution_policy_runtime import (  # noqa: E402
    resolve_worker_execution_policy,
)
from app.workspace_agents.config_loader import EmployeeConfig  # noqa: E402
from app.workspace_service_connections import (  # noqa: E402
    apply_live_service_policy,
    load_workspace_service_connections,
    parse_operator_dotenv,
    workspace_service_connection_posture,
)


class WorkspaceServiceConnectionTests(unittest.TestCase):
    def test_load_young_eagles_profile(self) -> None:
        connections = load_workspace_service_connections()
        profile = connections.get("workspace_young_eagles_day_care")
        self.assertIsNotNone(profile)
        assert profile is not None
        self.assertEqual(profile.product, "edudash_ops")
        self.assertEqual(profile.dashpro_tenant_id, "ba79097c-1b93-4b48-bcbe-df73878ab4d1")
        self.assertIn(("npm", "run", "check-supabase"), profile.live_verify_command_prefixes)

    def test_parse_operator_dotenv_whitelist_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text(
                "SUPABASE_URL=https://example.supabase.co\n"
                "SUPABASE_SERVICE_ROLE_KEY=secret\n"
                "OTHER=ignored\n",
                encoding="utf-8",
            )
            parsed = parse_operator_dotenv(
                root,
                ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"),
            )
        self.assertEqual(parsed["SUPABASE_URL"], "https://example.supabase.co")
        self.assertEqual(parsed["SUPABASE_SERVICE_ROLE_KEY"], "secret")
        self.assertNotIn("OTHER", parsed)

    def test_apply_live_service_policy_widens_backend(self) -> None:
        baseline = role_execution_policy("backend")
        self.assertEqual("none", baseline.network_mode)
        widened = apply_live_service_policy(
            baseline,
            workspace_id="workspace_young_eagles_day_care",
            role="backend",
        )
        self.assertEqual("audited", widened.network_mode)
        self.assertIn(("npm", "run", "check-supabase"), widened.approved_command_prefixes)

    @patch("app.workspace_service_connections.get_workspace_project_binding")
    @patch("app.workspace_service_connections.resolve_workspace_live_env")
    def test_posture_never_includes_secret_values(
        self,
        mock_env: unittest.mock.MagicMock,
        mock_binding: unittest.mock.MagicMock,
    ) -> None:
        mock_binding.return_value = unittest.mock.MagicMock(
            project_root=Path("/tmp/young-eagles"),
        )
        mock_env.return_value = {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "secret-value",
        }
        with patch.object(Path, "is_file", return_value=True):
            posture = workspace_service_connection_posture("workspace_young_eagles_day_care")
        encoded = json.dumps(posture)
        self.assertNotIn("secret-value", encoded)
        self.assertTrue(posture["env_keys_resolved"]["SUPABASE_URL"])

    @patch("app.workspace_service_connections.apply_live_service_policy")
    @patch("app.workspace_agents.execution_policy_runtime.load_repo_contract")
    def test_resolve_worker_policy_passes_workspace_id(
        self,
        mock_contract: unittest.mock.MagicMock,
        mock_apply: unittest.mock.MagicMock,
    ) -> None:
        mock_contract.return_value = {"allowed_paths": ["server"], "forbidden_path_globs": ["**/.env"]}
        baseline = role_execution_policy("backend")
        mock_apply.return_value = baseline
        resolve_worker_execution_policy(
            employee=EmployeeConfig(role="backend"),
            task_payload={"allowed_paths": ["server"]},
            workspace_root=Path("/tmp/checkout"),
            workspace_id="workspace_young_eagles_day_care",
        )
        mock_apply.assert_called_once()
        self.assertEqual(
            "workspace_young_eagles_day_care",
            mock_apply.call_args.kwargs["workspace_id"],
        )


if __name__ == "__main__":
    unittest.main()
