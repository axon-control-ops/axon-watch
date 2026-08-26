"""Source workspace preflight, safe Git bootstrap, and verification selection."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


RunCommand = Callable[..., Any]


@dataclass(frozen=True)
class WorkspacePreflight:
    path: str
    exists: bool
    is_dir: bool
    project_type: str
    verification_commands: tuple[str, ...]
    starter_workspace: bool
    issues: tuple[str, ...] = ()


_SENSITIVE_NAMES = {
    ".env",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
}
_STARTER_BOOTSTRAP_PATHS = (
    ".gitignore",
    "README.md",
    "notes.txt",
    "project.axon.yaml",
    "package.json",
    "package-lock.json",
    "config/env.example",
    ".github/workflows/ci.yml",
    "scripts/guardrails/check-workspace-health.sh",
    "tests/smoke.test.js",
)


def _read_json_object(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def detect_project_type(root: Path) -> str:
    if (root / "package.json").is_file():
        return "node"
    if (root / "pyproject.toml").is_file() or (root / "requirements.txt").is_file():
        return "python"
    if (root / "Cargo.toml").is_file():
        return "rust"
    if (root / "go.mod").is_file():
        return "go"
    starter_markers = ["README.md", "project.axon.yaml", "notes.txt"]
    if any((root / marker).is_file() for marker in starter_markers):
        return "starter"
    return "unknown"


def verification_commands_for_project(root: Path) -> tuple[str, ...]:
    package_json = root / "package.json"
    if package_json.is_file():
        package = _read_json_object(package_json) or {}
        scripts = package.get("scripts") if isinstance(package.get("scripts"), dict) else {}
        commands: list[str] = []
        if "test" in scripts:
            commands.append("npm test")
        if "lint" in scripts:
            commands.append("npm run lint")
        return tuple(commands)
    if (root / "pyproject.toml").is_file() and (root / "tests").is_dir():
        return ("python -m pytest",)
    if (root / "Cargo.toml").is_file():
        return ("cargo test",)
    if (root / "go.mod").is_file():
        return ("go test ./...",)
    return ()


def inspect_source_workspace(root: Path) -> WorkspacePreflight:
    expanded = root.expanduser()
    exists = expanded.exists()
    is_dir = expanded.is_dir()
    issues: list[str] = []
    project_type = "missing"
    commands: tuple[str, ...] = ()
    starter = False
    if not exists:
        issues.append("workspace path does not exist")
    elif not is_dir:
        issues.append("workspace path is not a directory")
    else:
        project_type = detect_project_type(expanded)
        commands = verification_commands_for_project(expanded)
        starter = project_type == "starter"
        if (expanded / "package.json").exists() and not (expanded / "package.json").is_file():
            issues.append("package.json exists but is not a file")
        if (expanded / "tests").exists() and not (expanded / "tests").is_dir():
            issues.append("tests exists but is not a directory")
    return WorkspacePreflight(
        path=str(expanded),
        exists=exists,
        is_dir=is_dir,
        project_type=project_type,
        verification_commands=commands,
        starter_workspace=starter,
        issues=tuple(issues),
    )


def safe_stage_candidate(path: str) -> bool:
    cleaned = str(path or "").strip().lstrip("./")
    if not cleaned or cleaned.startswith("../") or "/../" in cleaned:
        return False
    parts = tuple(part for part in cleaned.split("/") if part)
    if any(part in {".git", ".cursor", ".codex", ".axon-si", "node_modules", "secrets"} for part in parts):
        return False
    name = parts[-1] if parts else cleaned
    lower = name.lower()
    if lower in _SENSITIVE_NAMES or lower.startswith(".env."):
        return False
    if lower.endswith((".pem", ".p12", ".pfx", ".key")):
        return False
    lowered_path = cleaned.lower()
    if "private_key" in lowered_path or "access_token" in lowered_path:
        return False
    if lower.endswith(".receipt.json") or "health-receipt" in lower:
        return False
    return True


def safe_stage_candidates(root: Path) -> list[str]:
    """Return only known starter files, never an arbitrary workspace sweep."""
    return [
        relative
        for relative in _STARTER_BOOTSTRAP_PATHS
        if (root / relative).is_file() and safe_stage_candidate(relative)
    ]


def bootstrap_acceptance_summary(
    *,
    workspace_id: str,
    run_id: str,
    task_id: str | None,
    verification_command: str,
    exit_code: int,
    changed_paths: list[str],
    commit_sha: str,
    branch: str,
    remote_url: str,
    delivery_url: str | None = None,
) -> str:
    verdict = "acceptance=pass" if exit_code == 0 else "acceptance=fail"
    refs = [
        verdict,
        f"workspace={workspace_id}",
        f"run={run_id}",
        f"task={task_id or 'none'}",
        f"command={verification_command or 'bootstrap-contract'}",
        f"exit={exit_code}",
        f"changed_paths={len(changed_paths)}",
        f"commit={commit_sha}",
        f"branch={branch}",
        f"remote={remote_url}",
    ]
    if delivery_url:
        refs.append(f"delivery={delivery_url}")
    return " · ".join(refs)


def git_identity_issue(root: Path, run: RunCommand) -> str | None:
    name = run(["git", "config", "--get", "user.name"], cwd=root)
    email = run(["git", "config", "--get", "user.email"], cwd=root)
    missing: list[str] = []
    if getattr(name, "returncode", 1) != 0 or not str(getattr(name, "stdout", "") or "").strip():
        missing.append("user.name")
    if getattr(email, "returncode", 1) != 0 or not str(getattr(email, "stdout", "") or "").strip():
        missing.append("user.email")
    if missing:
        return "Git identity is missing: " + ", ".join(missing)
    return None


__all__ = [
    "WorkspacePreflight",
    "bootstrap_acceptance_summary",
    "detect_project_type",
    "git_identity_issue",
    "inspect_source_workspace",
    "safe_stage_candidate",
    "safe_stage_candidates",
    "verification_commands_for_project",
]
