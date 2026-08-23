"""Gate 6 immutable verifier check planning and evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from app.project_contract.loader import load_project_contract
from app.workspace_agents.diff_policy import (
    DiffPolicyFinding,
    evaluate_changed_paths,
    evaluate_diff_texts,
    resolve_effective_allowed_paths,
)

VERIFIER_IDENTITY = "verifier"
IMPLEMENTER_ROLES = frozenset({"implementer", "worker", "coder", "agent"})


@dataclass
class CheckResult:
    name: str
    passed: bool
    command: str = ""
    output_excerpt: str = ""
    actor: str = VERIFIER_IDENTITY

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AcceptanceEvaluation:
    passed: bool
    summary: str
    checks: list[CheckResult] = field(default_factory=list)
    policy_findings: list[DiffPolicyFinding] = field(default_factory=list)
    actor: str = VERIFIER_IDENTITY

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "summary": self.summary,
            "actor": self.actor,
            "checks": [check.to_dict() for check in self.checks],
            "policy_findings": [
                {"code": f.code, "path": f.path, "detail": f.detail}
                for f in self.policy_findings
            ],
        }


def assert_verifier_identity(actor: str) -> None:
    cleaned = str(actor or "").strip().lower()
    if cleaned in IMPLEMENTER_ROLES:
        raise ValueError(
            "Gate 6 verifier identity must be separate from the implementer",
        )
    if cleaned != VERIFIER_IDENTITY:
        raise ValueError(f"unexpected verifier actor: {actor}")


def build_check_plan(contract: dict[str, Any]) -> list[dict[str, str]]:
    required = list(contract.get("verifier", {}).get("required_checks") or [])
    commands = contract.get("commands") or {}
    plan: list[dict[str, str]] = []
    for name in required:
        cmd_list = commands.get(name) or []
        command = " && ".join(cmd_list) if cmd_list else f"<missing command:{name}>"
        plan.append({"name": name, "command": command})
    return plan


def evaluate_check_outputs(
    planned: Iterable[dict[str, str]],
    *,
    results_by_name: dict[str, dict[str, Any]],
    actor: str = VERIFIER_IDENTITY,
) -> list[CheckResult]:
    assert_verifier_identity(actor)
    checks: list[CheckResult] = []
    for item in planned:
        name = str(item.get("name") or "")
        command = str(item.get("command") or "")
        result = results_by_name.get(name) or {}
        passed = bool(result.get("passed"))
        excerpt = str(result.get("output_excerpt") or result.get("output") or "")[:2000]
        checks.append(
            CheckResult(
                name=name,
                passed=passed,
                command=command,
                output_excerpt=excerpt,
                actor=actor,
            )
        )
    return checks


def evaluate_acceptance(
    *,
    contract: dict[str, Any],
    check_results: dict[str, dict[str, Any]],
    changed_paths: Iterable[str] | None = None,
    path_to_text: dict[str, str] | None = None,
    task_allowed_paths: Iterable[str] | None = None,
    actor: str = VERIFIER_IDENTITY,
) -> AcceptanceEvaluation:
    assert_verifier_identity(actor)
    plan = build_check_plan(contract)
    checks = evaluate_check_outputs(plan, results_by_name=check_results, actor=actor)
    findings: list[DiffPolicyFinding] = []
    if changed_paths is not None:
        effective_allowed = resolve_effective_allowed_paths(
            contract_allowed_paths=contract.get("allowed_paths") or [],
            task_allowed_paths=task_allowed_paths or [],
            fail_closed_missing_task=True,
        )
        findings.extend(
            evaluate_changed_paths(
                changed_paths,
                allowed_paths=effective_allowed,
                forbidden_path_globs=contract.get("forbidden_path_globs") or [],
            )
        )
    if path_to_text:
        findings.extend(evaluate_diff_texts(path_to_text))

    failed_checks = [c.name for c in checks if not c.passed]
    passed = not failed_checks and not findings
    if passed:
        summary = "acceptance=pass · " + ",".join(c.name for c in checks) or "checks"
    else:
        parts = []
        if failed_checks:
            parts.append("failed_checks=" + ",".join(failed_checks))
        if findings:
            parts.append(
                "policy=" + ",".join(sorted({f.code for f in findings}))
            )
        summary = "acceptance=fail · " + "; ".join(parts)
    return AcceptanceEvaluation(
        passed=passed,
        summary=summary,
        checks=checks,
        policy_findings=findings,
        actor=actor,
    )


def load_repo_contract(repo_root: str | None = None) -> dict[str, Any]:
    from pathlib import Path

    from app.project_contract.loader import resolve_default_contract

    root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[4]
    return load_project_contract(resolve_default_contract(root))
