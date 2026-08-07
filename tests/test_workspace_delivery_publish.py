from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_delivery import publish  # noqa: E402


class WorkspaceDeliveryPublishTests(unittest.TestCase):
    def test_publish_stages_only_the_audited_paths(self) -> None:
        calls: list[list[str]] = []

        def fake_run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            calls.append(args)
            return subprocess.CompletedProcess(args, 0, "", "")

        with patch("app.workspace_delivery.publish._run", side_effect=fake_run):
            result = publish._stage_isolation_paths(
                Path("/tmp/isolated-worker"),
                ["services/control-plane/app/api.py", "tests/test_api.py"],
            )

        self.assertEqual(0, result.returncode)
        self.assertEqual(
            ["git", "add", "--", "services/control-plane/app/api.py", "tests/test_api.py"],
            calls[0],
        )


if __name__ == "__main__":
    unittest.main()
