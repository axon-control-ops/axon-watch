"""Gate 6 project contract, diff policy, and verifier check evaluation tests."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.project_contract.adapters import summarize_adapters  # noqa: E402
from app.project_contract.loader import (  # noqa: E402
    ProjectContractError,
    load_project_contract,
    resolve_default_contract,
)
from app.workspace_agents.diff_policy import evaluate_changed_paths, evaluate_diff_texts  # noqa: E402
from app.workspace_agents.verifier_checks import (  # noqa: E402
    PROOF_INCONCLUSIVE,
    PROOF_INSPECTED_ONLY,
    PROOF_REJECTED,
    PROOF_VERIFIED,
    evaluate_acceptance,
)


class Gate6ProjectContractTests(unittest.TestCase):
    def test_loads_repo_project_axon_yaml(self) -> None:
        path = resolve_default_contract(REPO_ROOT)
        contract = load_project_contract(path)
        self.assertEqual("workspace_axon_watch", contract["project_id"])
        self.assertIn("node_vue", contract["adapters"])
        self.assertIn("python_fastapi", contract["adapters"])
        self.assertIn("android_gradle", contract["adapters"])
        self.assertEqual("verifier", contract["verifier"]["identity"])
        self.assertTrue(contract["verifier"]["immutable_to_implementer"])
        statuses = summarize_adapters(contract["adapters"])
        self.assertTrue(all(item["supported"] for item in statuses))

    def test_unsupported_adapter_stays_inspect_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "project.axon.yaml"
            path.write_text(
                "\n".join(
                    [
                        "version: 1",
                        "project_id: demo",
                        "certification_level: inspect_only",
                        "adapters:",
                        "  - rust_unknown",
                        "commands:",
                        "verifier:",
                        "  identity: verifier",
                        "  required_checks: []",
                    ]
                ),
                encoding="utf-8",
            )
            contract = load_project_contract(path)
            self.assertTrue(contract["inspect_only"])
            self.assertEqual(["rust_unknown"], contract["unsupported_adapters"])

    def test_unsupported_adapter_rejects_non_inspect_certification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "project.axon.yaml"
            path.write_text(
                "\n".join(
                    [
                        "version: 1",
                        "project_id: demo",
                        "certification_level: build",
                        "adapters:",
                        "  - rust_unknown",
                        "commands:",
                        "verifier:",
                        "  identity: verifier",
                        "  required_checks: []",
                    ]
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ProjectContractError):
                load_project_contract(path)


class Gate6DiffPolicyTests(unittest.TestCase):
    def test_rejects_out_of_scope_and_secrets(self) -> None:
        findings = evaluate_changed_paths(
            ["apps/console-web/src/App.vue", "/etc/passwd", "secrets/token"],
            allowed_paths=["apps/", "services/"],
            forbidden_path_globs=["**/secrets/**"],
        )
        codes = {f.code for f in findings}
        self.assertIn("out_of_scope", codes)
        self.assertIn("forbidden_path", codes)
        secret_findings = evaluate_diff_texts(
            {"apps/x.ts": "const token = 'ghp_abcdefghijklmnopqrstuvwxyz012345'"}
        )
        self.assertTrue(any(f.code == "secret" for f in secret_findings))


class Gate6VerifierCheckEvalTests(unittest.TestCase):
    def test_failed_check_or_secret_blocks_acceptance(self) -> None:
        contract = load_project_contract(resolve_default_contract(REPO_ROOT))
        # Trim required checks for unit speed.
        contract = {
            **contract,
            "verifier": {
                **contract["verifier"],
                "required_checks": ["lint", "test"],
            },
            "commands": {
                "lint": ["echo lint"],
                "test": ["echo test"],
            },
        }
        # Acceptance now fails closed on scope when a task carries no explicit
        # write scope, so these calls declare one covering the changed path
        # (mirrors a real worker task's allowed_paths).
        task_scope = ["apps/console-web/src"]
        failed = evaluate_acceptance(
            contract=contract,
            check_results={
                "lint": {"passed": True, "output_excerpt": "ok"},
                "test": {"passed": False, "output_excerpt": "boom"},
            },
            changed_paths=["apps/console-web/src/App.vue"],
            task_allowed_paths=task_scope,
        )
        self.assertFalse(failed.passed)
        self.assertIn("failed_checks=test", failed.summary)

        blocked_secret = evaluate_acceptance(
            contract=contract,
            check_results={
                "lint": {"passed": True, "output_excerpt": "ok"},
                "test": {"passed": True, "output_excerpt": "ok"},
            },
            changed_paths=["apps/console-web/src/App.vue"],
            task_allowed_paths=task_scope,
            path_to_text={
                "apps/console-web/src/App.vue": "ak=AKIAIOSFODNN7EXAMPLE12",
            },
        )
        self.assertFalse(blocked_secret.passed)
        self.assertIn("policy=secret", blocked_secret.summary)

        passed = evaluate_acceptance(
            contract=contract,
            check_results={
                "lint": {"passed": True, "executed": True, "output_excerpt": "ok"},
                "test": {"passed": True, "executed": True, "output_excerpt": "ok"},
            },
            changed_paths=["apps/console-web/src/App.vue"],
            task_allowed_paths=task_scope,
            path_to_text={"apps/console-web/src/App.vue": "export const ok = true"},
        )
        self.assertTrue(passed.passed)
        self.assertEqual(PROOF_VERIFIED, passed.proof_strength)

    def test_zero_check_inspect_only_never_verifies(self) -> None:
        evaluated = evaluate_acceptance(
            contract={
                "project_id": "inspect",
                "certification_level": "inspect_only",
                "inspect_only": True,
                "commands": {},
                "allowed_paths": [],
                "forbidden_path_globs": [],
                "verifier": {"required_checks": []},
            },
            check_results={},
            changed_paths=[],
        )

        self.assertFalse(evaluated.passed)
        self.assertEqual(PROOF_INSPECTED_ONLY, evaluated.proof_strength)
        self.assertIn("proof=INSPECTED_ONLY", evaluated.summary)

    def test_missing_contract_fallback_is_inconclusive_without_policy_failure(self) -> None:
        evaluated = evaluate_acceptance(
            contract={
                "project_id": "inspect",
                "certification_level": "inspect_only",
                "inspect_only": True,
                "verification_unavailable_reason": "project_contract_unavailable",
                "commands": {},
                "allowed_paths": [],
                "forbidden_path_globs": [],
                "verifier": {"required_checks": []},
            },
            check_results={},
            changed_paths=[],
        )

        self.assertFalse(evaluated.passed)
        self.assertEqual(PROOF_INCONCLUSIVE, evaluated.proof_strength)
        self.assertIn("project_contract_unavailable", evaluated.summary)

    def test_skipped_only_checks_are_inconclusive(self) -> None:
        evaluated = evaluate_acceptance(
            contract={
                "project_id": "demo",
                "certification_level": "build",
                "inspect_only": False,
                "commands": {"build": ["npm run build"]},
                "allowed_paths": ["services/"],
                "forbidden_path_globs": [],
                "verifier": {"required_checks": ["build"]},
            },
            check_results={
                "build": {
                    "passed": True,
                    "executed": False,
                    "output_excerpt": "skipped: no console-web changes",
                }
            },
            changed_paths=["services/control-plane/app/example.py"],
        )

        self.assertFalse(evaluated.passed)
        self.assertEqual(PROOF_INCONCLUSIVE, evaluated.proof_strength)
        self.assertIn("checks=none", evaluated.summary)

    def test_policy_findings_reject_even_without_checks(self) -> None:
        evaluated = evaluate_acceptance(
            contract={
                "project_id": "inspect",
                "certification_level": "inspect_only",
                "inspect_only": True,
                "commands": {},
                "allowed_paths": [],
                "forbidden_path_globs": ["**/secrets/**"],
                "verifier": {"required_checks": []},
            },
            check_results={},
            changed_paths=["secrets/token"],
        )

        self.assertFalse(evaluated.passed)
        self.assertEqual(PROOF_REJECTED, evaluated.proof_strength)
        self.assertIn("policy=", evaluated.summary)

    def test_implementer_cannot_act_as_verifier(self) -> None:
        contract = load_project_contract(resolve_default_contract(REPO_ROOT))
        with self.assertRaises(ValueError):
            evaluate_acceptance(
                contract=contract,
                check_results={},
                actor="implementer",
            )


if __name__ == "__main__":
    unittest.main()
