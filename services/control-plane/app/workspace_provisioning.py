"""Provision a new workspace root into a deliverable current-platform repo."""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.workspace_delivery.config import clear_config_cache_for_tests, default_config_path
from app.workspace_delivery.gh_cli import resolve_gh_cli
from app.workspace_project_bindings import project_root_allowlist


class WorkspaceProvisioningError(ValueError):
    pass


@dataclass(frozen=True)
class WorkspaceProvisioningSpec:
    workspace_id: str
    project_root: Path
    display_name: str | None = None
    github_owner: str = "axon-control-ops"
    github_repo: str | None = None
    create_github_repo: bool = False
    private_repo: bool = True
    initialize_git: bool = True
    scaffold_files: bool = True
    include_ci_workflow: bool = False
    enable_delivery: bool = True


_REPO_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
_WORKSPACE_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")


def _slug_from_workspace_id(workspace_id: str) -> str:
    slug = workspace_id.strip()
    if slug.lower().startswith("workspace_"):
        slug = slug[10:]
    slug = re.sub(r"[^a-zA-Z0-9_.-]+", "-", slug).strip("._-")
    return slug.lower() or "workspace"


def _validate_workspace_id(workspace_id: str) -> str:
    value = workspace_id.strip()
    if not value or not _WORKSPACE_ID_RE.fullmatch(value):
        raise WorkspaceProvisioningError(
            "workspace_id may only contain letters, numbers, '_', '-', and '.'"
        )
    return value


def _validate_repo_name(repo: str) -> str:
    value = repo.strip()
    if not value or not _REPO_NAME_RE.fullmatch(value) or value in {".", ".."}:
        raise WorkspaceProvisioningError(
            "github_repo may only contain letters, numbers, '_', '-', and '.'"
        )
    return value


def _allowed_github_owners() -> frozenset[str]:
    raw = os.environ.get("AXON_WATCH_GITHUB_OWNER_ALLOWLIST", "").strip()
    owners = [item.strip() for item in raw.split(",") if item.strip()] if raw else []
    if not owners:
        owners = ["axon-control-ops"]
    return frozenset(owners)


def _validate_github_owner(owner: str) -> str:
    value = owner.strip()
    if not value:
        raise WorkspaceProvisioningError("github_owner is required")
    if value not in _allowed_github_owners():
        raise WorkspaceProvisioningError(
            f"github_owner must be one of: {', '.join(sorted(_allowed_github_owners()))}"
        )
    return value


def _validate_project_root_for_creation(root: Path) -> Path:
    resolved = root.expanduser().resolve()
    for allowed in project_root_allowlist():
        try:
            resolved.relative_to(allowed)
            return resolved
        except ValueError:
            continue
    raise WorkspaceProvisioningError(
        f"project_root is outside allowlist: {resolved}",
    )


def _run(
    args: list[str],
    *,
    cwd: Path,
    timeout: float = 60.0,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            args=args,
            returncode=124,
            stdout=str(exc.stdout or ""),
            stderr=(str(exc.stderr or "") + f"\ncommand timed out after {timeout}s").strip(),
        )


def _detail(completed: subprocess.CompletedProcess[str], *, fallback: str) -> str:
    text = (completed.stderr or completed.stdout or fallback).strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    compact = "\n".join(lines[-8:]) if lines else fallback
    if len(compact) <= 500:
        return compact
    return compact[-500:]


def _write_if_missing(path: Path, body: str, created: list[Path]) -> str:
    if path.exists():
        return "present"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    created.append(path)
    return "created"


def _package_name(repo: str) -> str:
    name = repo.lower()
    name = re.sub(r"[^a-z0-9_.-]+", "-", name).strip("._-")
    return name or "workspace"


def _scaffold_files(spec: WorkspaceProvisioningSpec) -> tuple[dict[str, str], list[Path]]:
    root = spec.project_root
    workspace_id = _validate_workspace_id(spec.workspace_id)
    display_name = (spec.display_name or workspace_id).strip() or workspace_id
    repo = _validate_repo_name(spec.github_repo or _slug_from_workspace_id(workspace_id))
    package_name = _package_name(repo)
    created: list[Path] = []
    statuses: dict[str, str] = {}

    statuses["README.md"] = _write_if_missing(
        root / "README.md",
        f"# {display_name}\n\nThis workspace is provisioned for AXON-X worker delivery.\n",
        created,
    )
    statuses[".gitignore"] = _write_if_missing(
        root / ".gitignore",
        "\n".join(
            [
                ".env",
                ".env.*",
                ".axon_terminal_history_*",
                ".axon_zcompdump*",
                ".cursor/",
                "node_modules/",
                "dist/",
                "coverage/",
                "npm-debug.log*",
                "",
            ]
        ),
        created,
    )
    package_json = {
        "name": package_name,
        "version": "1.0.0",
        "private": True,
        "scripts": {
            "test": "node --test tests/smoke.test.js",
        },
    }
    statuses["package.json"] = _write_if_missing(
        root / "package.json",
        json.dumps(package_json, indent=2, sort_keys=True) + "\n",
        created,
    )
    package_lock = {
        "name": package_name,
        "version": "1.0.0",
        "lockfileVersion": 3,
        "requires": True,
        "packages": {
            "": {
                "name": package_name,
                "version": "1.0.0",
            }
        },
    }
    statuses["package-lock.json"] = _write_if_missing(
        root / "package-lock.json",
        json.dumps(package_lock, indent=2, sort_keys=True) + "\n",
        created,
    )
    statuses["tests/smoke.test.js"] = _write_if_missing(
        root / "tests" / "smoke.test.js",
        "const test = require('node:test');\n"
        "const assert = require('node:assert/strict');\n\n"
        "test('workspace smoke baseline is wired', () => {\n"
        f"  assert.equal(process.env.npm_package_name, '{package_name}');\n"
        "});\n",
        created,
    )
    statuses["scripts/guardrails/check-workspace-health.sh"] = _write_if_missing(
        root / "scripts" / "guardrails" / "check-workspace-health.sh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n\n"
        "root=\"$(cd \"$(dirname \"${BASH_SOURCE[0]}\")/../..\" && pwd)\"\n"
        "cd \"$root\"\n\n"
        "test -d .git\n"
        "test -f project.axon.yaml\n"
        "test -f package.json\n"
        "npm test\n",
        created,
    )
    if statuses["scripts/guardrails/check-workspace-health.sh"] == "created":
        (root / "scripts" / "guardrails" / "check-workspace-health.sh").chmod(0o755)
    contract = f"""# Auto-scaffolded by AXON-X workspace provisioning.
version: 1
project_id: {workspace_id}
display_name: {display_name.replace('"', "'")}
stack: node
certification_level: build
environment:
  bootstrap:
    - npm ci
commands:
  test:
    - npm test
allowed_paths:
  - docs/
  - scripts/
  - tests/
  - package.json
  - package-lock.json
  - README.md
  - project.axon.yaml
forbidden_path_globs:
  - "**/.env"
  - "**/.env.local"
  - "**/secrets/**"
verifier:
  required_checks:
    - test
"""
    statuses["project.axon.yaml"] = _write_if_missing(
        root / "project.axon.yaml",
        contract,
        created,
    )
    if spec.include_ci_workflow:
        workflow = f"""name: CI

on:
  pull_request:
  push:
    branches:
      - main

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
      - run: npm ci
      - run: npm test
"""
        statuses[".github/workflows/ci.yml"] = _write_if_missing(
            root / ".github" / "workflows" / "ci.yml",
            workflow,
            created,
        )
    return statuses, created


def _ensure_git_repo(root: Path, created_files: list[Path]) -> dict[str, Any]:
    report: dict[str, Any] = {"created_initial_commit": False}
    if not (root / ".git").exists():
        completed = _run(["git", "init", "-b", "main"], cwd=root)
        if completed.returncode != 0:
            raise WorkspaceProvisioningError(
                "git init failed: " + _detail(completed, fallback="git init failed")
            )
        report["initialized"] = True
    else:
        report["initialized"] = False

    if created_files:
        relative_files = [str(path.relative_to(root)) for path in created_files]
        completed = _run(["git", "add", "--", *relative_files], cwd=root)
        if completed.returncode != 0:
            raise WorkspaceProvisioningError(
                "git add failed: " + _detail(completed, fallback="git add failed")
            )
        completed = _run(
            [
                "git",
                "-c",
                "user.name=AXON-X Workspace Provisioner",
                "-c",
                "user.email=workspace-provisioner@axon.local",
                "commit",
                "-m",
                "chore: bootstrap workspace",
            ],
            cwd=root,
        )
        if completed.returncode == 0:
            report["created_initial_commit"] = True
        else:
            detail = _detail(completed, fallback="git commit failed")
            if "nothing to commit" not in detail.lower():
                raise WorkspaceProvisioningError("git commit failed: " + detail)
    branch = _run(["git", "branch", "--show-current"], cwd=root)
    report["branch"] = (branch.stdout or "").strip() or "main"
    return report


def _ensure_remote_origin(root: Path, *, owner: str, repo: str) -> dict[str, Any]:
    expected = f"https://github.com/{owner}/{repo}.git"
    current = _run(["git", "remote", "get-url", "origin"], cwd=root)
    if current.returncode == 0:
        url = (current.stdout or "").strip()
        if url != expected:
            raise WorkspaceProvisioningError(
                f"git origin already points at {url}; refusing to overwrite it"
            )
        return {"status": "present", "url": expected}
    completed = _run(["git", "remote", "add", "origin", expected], cwd=root)
    if completed.returncode != 0:
        raise WorkspaceProvisioningError(
            "git remote add failed: " + _detail(completed, fallback="git remote add failed")
        )
    return {"status": "created", "url": expected}


def _ensure_github_repo(
    root: Path,
    *,
    owner: str,
    repo: str,
    private: bool,
) -> dict[str, Any]:
    gh = resolve_gh_cli()
    if gh is None:
        raise WorkspaceProvisioningError(
            "gh CLI is required to create the GitHub repository; install gh or set AXON_WATCH_GH_CLI_PATH"
        )
    full_name = f"{owner}/{repo}"
    view = _run([gh, "repo", "view", full_name, "--json", "name"], cwd=root)
    created = False
    if view.returncode != 0:
        args = [gh, "repo", "create", full_name]
        args.append("--private" if private else "--public")
        args.extend(["--description", f"AXON-X workspace repository for {repo}"])
        create = _run(args, cwd=root, timeout=120.0)
        if create.returncode != 0:
            raise WorkspaceProvisioningError(
                "github repo create failed: "
                + _detail(create, fallback="github repo create failed")
            )
        created = True
    remote = _ensure_remote_origin(root, owner=owner, repo=repo)
    push = _run(["git", "push", "-u", "origin", "main"], cwd=root, timeout=120.0)
    if push.returncode != 0:
        raise WorkspaceProvisioningError(
            "git push failed: " + _detail(push, fallback="git push failed")
        )
    return {
        "status": "created" if created else "present",
        "full_name": full_name,
        "remote": remote,
        "pushed": True,
    }


def upsert_workspace_delivery_policy(
    *,
    workspace_id: str,
    github_owner: str,
    github_repo: str,
    base_branch: str = "main",
    workflow_names: list[str] | None = None,
    config_path: Path | None = None,
) -> dict[str, Any]:
    path = config_path or default_config_path()
    row = {
        "workspace_id": workspace_id,
        "enabled": True,
        "base_branch": base_branch,
        "github_owner": github_owner,
        "github_repo": github_repo,
        "workflow_names": workflow_names or [],
        "attempt_budget": 3,
        "push_policy": "draft_pr",
        "notes": (
            "Provisioned workspace delivery opens draft PRs into the standalone "
            f"{github_owner}/{github_repo} repository."
        ),
    }
    payload: dict[str, Any]
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkspaceProvisioningError(f"unable to read delivery config: {path}") from exc
        if not isinstance(loaded, dict):
            raise WorkspaceProvisioningError("delivery config must contain a JSON object")
        payload = loaded
    else:
        payload = {
            "schema_version": 1,
            "defaults": {
                "enabled": True,
                "push_policy": "draft_pr",
                "attempt_budget": 3,
                "protected_branches": ["main", "master", "dev", "production", "release"],
            },
            "workspaces": [],
        }
    rows = payload.setdefault("workspaces", [])
    if not isinstance(rows, list):
        raise WorkspaceProvisioningError("delivery config workspaces must be a list")
    replaced = False
    for index, existing in enumerate(rows):
        if isinstance(existing, dict) and existing.get("workspace_id") == workspace_id:
            rows[index] = {**existing, **row}
            replaced = True
            break
    if not replaced:
        rows.append(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    tmp_path.replace(path)
    clear_config_cache_for_tests()
    return {"status": "updated" if replaced else "created", "path": str(path), "policy": row}


def provision_workspace_project(spec: WorkspaceProvisioningSpec) -> dict[str, Any]:
    workspace_id = _validate_workspace_id(spec.workspace_id)
    owner = _validate_github_owner(spec.github_owner)
    repo = _validate_repo_name(spec.github_repo or _slug_from_workspace_id(workspace_id))
    root = _validate_project_root_for_creation(spec.project_root)
    root.mkdir(parents=True, exist_ok=True)

    result: dict[str, Any] = {
        "workspace_id": workspace_id,
        "project_root": str(root),
        "github_owner": owner,
        "github_repo": repo,
    }
    created_files: list[Path] = []
    if spec.scaffold_files:
        scaffold, created_files = _scaffold_files(
            WorkspaceProvisioningSpec(
                workspace_id=workspace_id,
                project_root=root,
                display_name=spec.display_name,
                github_owner=owner,
                github_repo=repo,
                create_github_repo=spec.create_github_repo,
                private_repo=spec.private_repo,
                initialize_git=spec.initialize_git,
                scaffold_files=spec.scaffold_files,
                include_ci_workflow=spec.include_ci_workflow,
                enable_delivery=spec.enable_delivery,
            )
        )
        result["scaffold"] = scaffold
        result["created_files"] = [str(path.relative_to(root)) for path in created_files]
    if spec.initialize_git or spec.create_github_repo:
        result["git"] = _ensure_git_repo(root, created_files)
    if spec.create_github_repo:
        result["github"] = _ensure_github_repo(
            root,
            owner=owner,
            repo=repo,
            private=spec.private_repo,
        )
    if spec.enable_delivery:
        result["delivery"] = upsert_workspace_delivery_policy(
            workspace_id=workspace_id,
            github_owner=owner,
            github_repo=repo,
            workflow_names=["CI"] if spec.include_ci_workflow else [],
        )
    result["status"] = "ready"
    return result


def maybe_provision_workspace_registration(body: Any) -> dict[str, Any] | None:
    if not bool(getattr(body, "provision", False) or getattr(body, "create_github_repo", False)):
        return None
    return provision_workspace_project(
        WorkspaceProvisioningSpec(
            workspace_id=str(getattr(body, "workspace_id", "")),
            project_root=Path(str(getattr(body, "project_root", ""))),
            display_name=getattr(body, "display_name", None),
            github_owner=str(getattr(body, "github_owner", "axon-control-ops")),
            github_repo=getattr(body, "github_repo", None),
            create_github_repo=bool(getattr(body, "create_github_repo", False)),
            private_repo=bool(getattr(body, "private_repo", True)),
            initialize_git=bool(getattr(body, "initialize_git", True)),
            include_ci_workflow=bool(getattr(body, "include_ci_workflow", False)),
            enable_delivery=bool(getattr(body, "enable_delivery", True)),
        )
    )


def register_workspace_with_optional_provision(body: Any) -> dict[str, Any]:
    from app.workspace_catalog import get_workspace_record
    from app.workspace_project_bindings import upsert_workspace_project_binding

    provisioning = maybe_provision_workspace_registration(body)
    binding = upsert_workspace_project_binding(
        workspace_id=str(getattr(body, "workspace_id", "")),
        project_root=str(getattr(body, "project_root", "")),
        display_name=getattr(body, "display_name", None),
    )
    record = get_workspace_record(binding.workspace_id)
    response: dict[str, Any] = {"workspace": record, "created": True}
    if provisioning is not None:
        response["provisioning"] = provisioning
    return response


__all__ = [
    "WorkspaceProvisioningError",
    "WorkspaceProvisioningSpec",
    "maybe_provision_workspace_registration",
    "provision_workspace_project",
    "register_workspace_with_optional_provision",
    "upsert_workspace_delivery_policy",
]
