"""Fail-fast checks before sandboxed agent dispatch."""

from __future__ import annotations

import shutil
from pathlib import Path

from app.cli_runtime.agent_sandbox import AgentSandboxPolicy, SandboxConfigurationError


def validate_agent_dispatch_preflight(
    *,
    family: str,
    runtime_binary: str,
    sandbox_policy: AgentSandboxPolicy | None,
) -> None:
    """Raise SandboxConfigurationError when dispatch prerequisites are missing."""
    issues: list[str] = []
    cleaned_family = str(family or "").strip().lower()
    binary = str(runtime_binary or "").strip()

    if sandbox_policy is not None and shutil.which("bwrap") is None:
        issues.append(
            "Bubblewrap (bwrap) is required for sandboxed agent dispatch but was not found in PATH."
        )

    if cleaned_family == "cursor" and binary:
        try:
            Path(binary).expanduser().resolve(strict=True)
        except OSError:
            issues.append(f"Cursor runtime binary does not exist: {binary}")

    if sandbox_policy is not None and shutil.which("rg") is None:
        issues.append(
            "ripgrep (rg) is required inside the agent sandbox PATH but was not found on the host. "
            "Install ripgrep on the control-plane host and DashPro self-hosted runners."
        )

    if sandbox_policy is not None and shutil.which("git") is None:
        issues.append(
            "git is required for isolated worker checkouts but was not found in PATH."
        )

    if sandbox_policy is not None and shutil.which("node") is None:
        issues.append(
            "node is required for workflow scripts and CI tooling but was not found in PATH."
        )

    if issues:
        raise SandboxConfigurationError("Agent dispatch preflight failed: " + " ".join(issues))
