from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.open_file_intent import (  # noqa: E402
    open_file_ui_action,
    resolve_open_file_intent,
)


class OpenFileIntentTests(unittest.TestCase):
    def test_detects_open_generated_image_prompt(self) -> None:
        intent = resolve_open_file_intent(
            "open the generated image for me",
            workspace_id="workspace_alpha",
        )
        self.assertIsNone(intent)

    def test_open_file_ui_action_payload(self) -> None:
        from app.chat.open_file_intent import OpenFileIntent  # noqa: E402

        payload = open_file_ui_action(
            OpenFileIntent(open_file_path="assets/mockup.png"),
            workspace_id="workspace_axon_watch",
        )
        self.assertEqual(
            {
                "type": "open_source",
                "workspace_id": "workspace_axon_watch",
                "open_file_path": "assets/mockup.png",
            },
            payload,
        )

    def test_resolves_latest_assets_image(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            workspace_root = Path(tempdir) / "workspace_axon_watch"
            assets_dir = workspace_root / "assets"
            assets_dir.mkdir(parents=True)
            image_path = assets_dir / "mockup.png"
            image_path.write_bytes(b"\x89PNG\r\n\x1a\n")

            from app.chat import open_file_intent as open_file_intent_module  # noqa: E402

            original = open_file_intent_module.resolve_workspace_root

            def fake_resolve(workspace_id: str) -> Path:
                if workspace_id == "workspace_axon_watch":
                    return workspace_root
                return original(workspace_id)

            open_file_intent_module.resolve_workspace_root = fake_resolve
            try:
                intent = resolve_open_file_intent(
                    "open the generated image for me",
                    workspace_id="workspace_axon_watch",
                )
            finally:
                open_file_intent_module.resolve_workspace_root = original

        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual("assets/mockup.png", intent.open_file_path)

    def test_resolves_explicit_image_path(self) -> None:
        intent = resolve_open_file_intent(
            "open assets/mockup.png",
            workspace_id="workspace_alpha",
        )
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual("assets/mockup.png", intent.open_file_path)


if __name__ == "__main__":
    unittest.main()
