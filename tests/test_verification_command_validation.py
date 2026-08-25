from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.verification_execution import (  # noqa: E402
    _verification_command_is_valid,
    extract_verification_commands,
    select_verification_commands,
)


class VerificationCommandValidationTests(unittest.TestCase):
    def test_rejects_bare_npm_run(self) -> None:
        self.assertFalse(_verification_command_is_valid("npm run"))

    def test_rejects_bare_npx_tsx(self) -> None:
        self.assertFalse(_verification_command_is_valid("npx --no-install tsx"))

    def test_accepts_npm_run_with_script(self) -> None:
        self.assertTrue(_verification_command_is_valid("npm run verify:contracts"))

    def test_accepts_ops_tsx_script(self) -> None:
        self.assertTrue(
            _verification_command_is_valid(
                "npx --no-install tsx services/ops/fix-mebelo-email-password.ts"
            )
        )

    def test_select_prefers_script_over_catalog_commands(self) -> None:
        goal = (
            "Verification after Marco (backend): `npm run`; `npx --no-install tsx`; "
            "`npx --no-install tsx services/ops/fix-mebelo-email-password.ts`"
        )
        commands = select_verification_commands(extract_verification_commands(goal), limit=3)
        self.assertEqual(
            ["npx --no-install tsx services/ops/fix-mebelo-email-password.ts"],
            commands,
        )


if __name__ == "__main__":
    unittest.main()
