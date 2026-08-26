"""Missing-file scaffold for current-platform workspace repositories."""

from __future__ import annotations

import json
import re
from pathlib import Path


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


def scaffold_workspace_files(
    *,
    root: Path,
    workspace_id: str,
    display_name: str | None,
    github_repo: str,
    include_ci_workflow: bool,
) -> tuple[dict[str, str], list[Path]]:
    label = (display_name or workspace_id).strip() or workspace_id
    package_name = _package_name(github_repo)
    created: list[Path] = []
    statuses: dict[str, str] = {}

    statuses["README.md"] = _write_if_missing(
        root / "README.md",
        f"# {label}\n\nThis workspace is provisioned for AXON-X worker delivery.\n",
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
display_name: {label.replace('"', "'")}
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
    if include_ci_workflow:
        workflow = """name: CI

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


__all__ = ["scaffold_workspace_files"]
