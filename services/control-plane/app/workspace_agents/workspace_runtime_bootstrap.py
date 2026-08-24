"""Automatic runtime provisioning for bound workspaces (current and future).

Ensures npm toolchains, project contracts, host utilities, and PATH are ready
before worker isolation or agent dispatch — so specialists like Vera are not
blocked by missing jest, awk, or unscoped terminal sessions.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_HOST_RUNTIME_TOOLS = (
    "awk",
    "git",
    "node",
    "npm",
    "python3",
    "rg",
    "bash",
    "sh",
)

# Optional but recommended for PDF/document workflows; missing tools degrade, not block.
_HOST_DOCUMENT_TOOLS = (
    "pdftotext",
    "pdftoppm",
)

_MINIMAL_CONTRACT_TEMPLATE = """# Auto-scaffolded by Axon workspace runtime bootstrap.
version: 1
project_id: {workspace_id}
display_name: {display_name}
stack: node
certification_level: inspect_only
environment:
  bootstrap:
    - npm ci
commands:
  test:
    - npm test --if-present
  lint:
    - npm run lint --if-present
allowed_paths:
  - apps/
  - src/
  - lib/
  - server/
  - services/
  - scripts/
  - tests/
  - docs/
  - config/
  - website/
  - output/
  - assets/
  - package.json
  - package-lock.json
  - README.md
  - project.axon.yaml
  - node_modules/
forbidden_path_globs:
  - "**/.env"
  - "**/.env.local"
  - "**/secrets/**"
verifier:
  required_checks:
    - test
"""


def _npm_project_needs_install(project_root: Path) -> bool:
    package_json = project_root / "package.json"
    if not package_json.is_file():
        return False
    modules = project_root / "node_modules"
    if not modules.is_dir() or not any(modules.iterdir()):
        return True
    jest_bin = modules / ".bin" / "jest"
    if jest_bin.exists():
        return False
    # Non-jest repos still need node_modules when dependencies exist.
    try:
        import json

        payload = json.loads(package_json.read_text(encoding="utf-8"))
        deps = payload.get("dependencies") or {}
        dev = payload.get("devDependencies") or {}
        return bool(deps or dev)
    except (OSError, json.JSONDecodeError):
        return True


_NPM_NOISE_PREFIXES = ("npm warn", "npm notice", "npm WARN", "npm notice ")


def npm_failure_detail(stderr: str, stdout: str, *, limit: int = 400) -> str:
    """Pick the line(s) that actually explain an npm failure.

    npm writes deprecation warnings to stderr on a *successful* install too, so
    taking the head of stderr surfaced e.g. "npm warn deprecated uuid@7.0.3..."
    as the reason dispatch was blocked. That sent operators chasing an
    unrelated transitive dependency while the real error -- which npm prints
    last, as "npm error ..." -- was truncated away entirely.
    """
    lines = [line.rstrip() for line in f"{stderr}\n{stdout}".splitlines() if line.strip()]
    real_errors = [
        line
        for line in lines
        if not line.lstrip().startswith(_NPM_NOISE_PREFIXES)
    ]
    chosen = real_errors or lines
    if not chosen:
        return "npm install failed"
    # npm prints the actionable error last; keep the tail, not the head.
    detail = "\n".join(chosen[-12:]).strip()
    if len(detail) <= limit:
        return detail
    return f"…{detail[-(limit - 1):]}"


def ensure_npm_toolchain(project_root: Path) -> dict[str, Any]:
    """Install npm dependencies when package.json exists but node_modules is absent."""
    root = project_root.expanduser().resolve()
    if not (root / "package.json").is_file():
        return {"status": "skipped", "reason": "no package.json"}
    if not _npm_project_needs_install(root):
        return {"status": "ready", "project_root": str(root)}

    logger.info("workspace runtime bootstrap: installing npm deps in %s", root)
    completed = subprocess.run(
        ["npm", "ci"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        logger.warning("npm ci failed for %s (%s); retrying npm install", root, completed.stderr[:200])
        completed = subprocess.run(
            ["npm", "install"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
    if completed.returncode != 0:
        return {
            "status": "failed",
            "project_root": str(root),
            "detail": npm_failure_detail(completed.stderr, completed.stdout),
        }
    return {"status": "installed", "project_root": str(root)}


def ensure_bound_python_venv(project_root: Path) -> dict[str, Any]:
    """Install requirements.txt into bound project .venv when document scripts need it."""
    root = project_root.expanduser().resolve()
    req = root / "requirements.txt"
    if not req.is_file():
        return {"status": "skipped", "reason": "no requirements.txt"}
    python_bin = root / ".venv" / "bin" / "python3"
    if python_bin.is_file():
        return {"status": "ready", "project_root": str(root)}
    try:
        completed = subprocess.run(
            ["python3", "-m", "venv", str(root / ".venv")],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            return {
                "status": "failed",
                "detail": (completed.stderr or completed.stdout or "venv create failed")[:400],
            }
        pip = root / ".venv" / "bin" / "pip"
        completed = subprocess.run(
            [str(pip), "install", "-r", str(req)],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            return {
                "status": "failed",
                "detail": (completed.stderr or completed.stdout or "pip install failed")[:400],
            }
    except OSError as exc:
        return {"status": "failed", "detail": str(exc)}
    return {"status": "installed", "project_root": str(root)}


def ensure_project_contract(
    *,
    workspace_id: str,
    project_root: Path,
    display_name: str | None = None,
) -> dict[str, Any]:
    """Scaffold a minimal project.axon.yaml when a bound repo lacks one."""
    root = project_root.expanduser().resolve()
    contract_path = root / "project.axon.yaml"
    if contract_path.is_file():
        return {"status": "present", "path": str(contract_path)}
    label = (display_name or workspace_id).strip() or workspace_id
    body = _MINIMAL_CONTRACT_TEMPLATE.format(
        workspace_id=workspace_id.strip(),
        display_name=label.replace('"', "'"),
    )
    try:
        contract_path.write_text(body, encoding="utf-8")
    except OSError as exc:
        return {"status": "failed", "detail": str(exc)}
    logger.info("workspace runtime bootstrap: wrote %s", contract_path)
    return {"status": "created", "path": str(contract_path)}


def check_host_runtime_tools() -> dict[str, Any]:
    """Report missing host utilities agents expect (awk, git, node, …)."""
    missing = [tool for tool in _HOST_RUNTIME_TOOLS if shutil.which(tool) is None]
    missing_document = [
        tool for tool in _HOST_DOCUMENT_TOOLS if shutil.which(tool) is None
    ]
    return {
        "ok": not missing,
        "missing": missing,
        "document_tools_missing": missing_document,
    }


def provision_workspace_runtime(
    workspace_id: str,
    *,
    project_root: Path | str | None = None,
    display_name: str | None = None,
    install_npm: bool = True,
    scaffold_contract: bool = True,
) -> dict[str, Any]:
    """Best-effort provisioning for one workspace binding."""
    from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root

    clean_id = str(workspace_id or "").strip()
    root: Path | None = None
    if project_root is not None:
        root = Path(project_root).expanduser().resolve()
    elif clean_id:
        try:
            root = resolve_workspace_root(clean_id)
        except WorkspaceRootError:
            root = None

    result: dict[str, Any] = {
        "workspace_id": clean_id,
        "project_root": str(root) if root is not None else None,
        "host_tools": check_host_runtime_tools(),
    }
    if root is None or not root.is_dir():
        result["status"] = "skipped"
        result["reason"] = "no bound project root"
        return result

    if scaffold_contract and clean_id:
        result["contract"] = ensure_project_contract(
            workspace_id=clean_id,
            project_root=root,
            display_name=display_name,
        )
    if install_npm:
        result["npm"] = ensure_npm_toolchain(root)
    result["python"] = ensure_bound_python_venv(root)

    host_ok = bool(result["host_tools"].get("ok"))
    npm_status = str((result.get("npm") or {}).get("status") or "")
    python_status = str((result.get("python") or {}).get("status") or "")
    npm_ok = npm_status in {"ready", "installed", "skipped"}
    python_ok = python_status in {"ready", "installed", "skipped"}
    result["status"] = "ready" if host_ok and npm_ok and python_ok else "degraded"
    return result


def ensure_workspace_runtime_ready(workspace_id: str) -> None:
    """Raise when host tools or npm toolchain block dispatch."""
    from app.cli_runtime.agent_sandbox import SandboxConfigurationError

    report = provision_workspace_runtime(workspace_id)
    host = report.get("host_tools") or {}
    missing = [str(item) for item in (host.get("missing") or []) if str(item).strip()]
    if missing:
        raise SandboxConfigurationError(
            "Workspace runtime host tools missing: "
            + ", ".join(missing)
            + ". Run ./scripts/ops/install-agent-sandbox-host-deps.sh "
            "(and ensure coreutils/gawk for awk)."
        )
    npm = report.get("npm") or {}
    if str(npm.get("status") or "") == "failed":
        detail = str(npm.get("detail") or "npm install failed")
        raise SandboxConfigurationError(
            f"Workspace npm toolchain is not ready: {detail}"
        )
    python = report.get("python") or {}
    if str(python.get("status") or "") == "failed":
        detail = str(python.get("detail") or "python venv install failed")
        raise SandboxConfigurationError(
            f"Workspace python document venv is not ready: {detail}"
        )


__all__ = [
    "check_host_runtime_tools",
    "ensure_bound_python_venv",
    "ensure_npm_toolchain",
    "npm_failure_detail",
    "ensure_project_contract",
    "ensure_workspace_runtime_ready",
    "provision_workspace_runtime",
]
