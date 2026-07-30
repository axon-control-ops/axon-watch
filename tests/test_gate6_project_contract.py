"""Gate 6 project contract, diff policy, and verifier check evaluation tests."""

from __future__ import annotations

import subprocess
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
    evaluate_acceptance,
)

# Constructed at runtime so the source file itself does not trip Gate 6 secret scan.
_FAKE_GHP = "ghp_" + "abcdefghijklmnopqrstuvwxyz012345"
_FAKE_AKIA = "AKIA" + "IOSFODNN7EXAMPLE" + "12"


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
            {"apps/x.ts": f"const token = '{_FAKE_GHP}'"}
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
        failed = evaluate_acceptance(
            contract=contract,
            check_results={
                "lint": {"passed": True, "output_excerpt": "ok"},
                "test": {"passed": False, "output_excerpt": "boom"},
            },
            changed_paths=["apps/console-web/src/App.vue"],
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
            path_to_text={
                "apps/console-web/src/App.vue": f"ak={_FAKE_AKIA}",
            },
        )
        self.assertFalse(blocked_secret.passed)
        self.assertIn("policy=secret", blocked_secret.summary)

        passed = evaluate_acceptance(
            contract=contract,
            check_results={
                "lint": {"passed": True, "output_excerpt": "ok"},
                "test": {"passed": True, "output_excerpt": "ok"},
            },
            changed_paths=["apps/console-web/src/App.vue"],
            path_to_text={"apps/console-web/src/App.vue": "export const ok = true"},
        )
        self.assertTrue(passed.passed)

    def test_implementer_cannot_act_as_verifier(self) -> None:
        contract = load_project_contract(resolve_default_contract(REPO_ROOT))
        with self.assertRaises(ValueError):
            evaluate_acceptance(
                contract=contract,
                check_results={},
                actor="implementer",
            )

    def test_list_changed_paths_excludes_axon_si_sidecar(self) -> None:
        from app.workspace_agents.verifier_runner import list_changed_paths

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sidecar = root / ".axon-si"
            sidecar.mkdir()
            (sidecar / "baseline.json").write_text("{}", encoding="utf-8")
            (root / "services").mkdir()
            (root / "services" / "note.txt").write_text("x\n", encoding="utf-8")
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "gate6@test"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "gate6"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            paths = list_changed_paths(root)
            self.assertIn("services/note.txt", paths)
            self.assertFalse(
                any(p == ".axon-si" or p.startswith(".axon-si/") for p in paths)
            )

    def test_repo_contract_wires_isolation_gate6_commands(self) -> None:
        contract = load_project_contract(resolve_default_contract(REPO_ROOT))
        allowed = contract.get("allowed_paths") or []
        self.assertIn("project.axon.yaml", [str(p) for p in allowed])
        commands = contract.get("commands") or {}
        self.assertIn("run_gate6_typecheck.sh", " ".join(commands.get("typecheck") or []))
        self.assertIn("run_gate6_tests.sh", " ".join(commands.get("test") or []))
        self.assertIn("run_gate6_build.sh", " ".join(commands.get("build") or []))


if __name__ == "__main__":
    unittest.main()
