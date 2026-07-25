#!/usr/bin/env python3
"""Standalone mirror of Rust host policy for CI without GTK deps."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.host_context.policy import classify_action  # noqa: E402


class HostPolicyParityTests(unittest.TestCase):
    def test_parity_matrix(self) -> None:
        cases = [
            ("open.path", "/home/edp/Documents/a.pdf", "auto"),
            ("open.path", "/home/edp/.ssh/id_rsa", "confirm"),
            ("shell.execute", None, "deny"),
            ("clipboard.read", None, "confirm"),
            ("bridge.heartbeat", None, "auto"),
            ("file.delete", None, "deny"),
        ]
        for action, path, expected in cases:
            self.assertEqual(expected, classify_action(action, path=path), msg=f"{action} {path}")


if __name__ == "__main__":
    unittest.main()
