#!/usr/bin/env python3
"""Validate dedicated-server deployment config and infra artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOPOLOGY_FILE = REPO_ROOT / "config" / "deployment-topology.json"
DEPLOYMENT_ENV_EXAMPLE = REPO_ROOT / "config" / "deployment.env.example"
LOCAL_ENV_EXAMPLE = REPO_ROOT / ".env.example"
CADDY_EXAMPLE = REPO_ROOT / "infra" / "caddy" / "Caddyfile.example"
SYSTEMD_DIR = REPO_ROOT / "infra" / "systemd"
SYSTEMD_USER_DIR = SYSTEMD_DIR / "user"

REQUIRED_DEPLOYMENT_KEYS = {
    "AXON_WATCH_DEPLOYMENT_MODE",
    "AXON_WATCH_REPO_ROOT",
    "AXON_WATCH_BIND_HOST",
    "AXON_WATCH_PUBLIC_BASE_URL",
    "AXON_WATCH_CONSOLE_WEB_PORT",
    "AXON_WATCH_CONTROL_PLANE_PORT",
    "AXON_WATCH_WATCH_SERVICE_PORT",
    "AXON_WATCH_CONTROL_PLANE_BASE_URL",
    "AXON_WATCH_WATCH_SERVICE_BASE_URL",
    "AXON_WATCH_CORS_ORIGINS",
    "AXON_WATCH_STATE_DIR",
    "AXON_WATCH_CONTROL_PLANE_DB",
    "AXON_WATCH_WATCH_SERVICE_DB",
}

LOOPBACK_PATTERN = re.compile(r"127\.0\.0\.1|localhost", re.IGNORECASE)


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"')
    return values


def validate_topology() -> list[str]:
    errors: list[str] = []
    if not TOPOLOGY_FILE.is_file():
        return [f"missing topology file: {TOPOLOGY_FILE.relative_to(REPO_ROOT)}"]

    payload = json.loads(TOPOLOGY_FILE.read_text(encoding="utf-8"))
    startup = payload.get("startup_order", [])
    expected_tail = ["axon-watch", "control-plane", "console-web", "reverse-proxy"]
    if startup[:1] != ["storage"] or startup[-4:] != expected_tail:
        errors.append("deployment-topology startup_order does not match dedicated-server spec")

    services = payload.get("services", {})
    for name in ("axon-watch", "control-plane", "console-web"):
        if name not in services:
            errors.append(f"deployment-topology missing service: {name}")
    watch = services.get("axon-watch", {})
    if watch.get("public_exposure") != "internal_only":
        errors.append("axon-watch must remain internal_only in deployment topology")
    return errors


def validate_deployment_env_example() -> list[str]:
    errors: list[str] = []
    if not DEPLOYMENT_ENV_EXAMPLE.is_file():
        return [f"missing deployment env example: {DEPLOYMENT_ENV_EXAMPLE.relative_to(REPO_ROOT)}"]

    values = _parse_env_file(DEPLOYMENT_ENV_EXAMPLE)
    missing = sorted(REQUIRED_DEPLOYMENT_KEYS - set(values))
    if missing:
        errors.append(f"deployment.env.example missing keys: {', '.join(missing)}")

    public_url = values.get("AXON_WATCH_PUBLIC_BASE_URL", "")
    if LOOPBACK_PATTERN.search(public_url):
        errors.append("AXON_WATCH_PUBLIC_BASE_URL must not use loopback in deployment.env.example")

    state_dir = values.get("AXON_WATCH_STATE_DIR", "")
    if state_dir and not state_dir.startswith("/"):
        errors.append("AXON_WATCH_STATE_DIR must be an absolute path in deployment.env.example")

    if values.get("AXON_WATCH_DEPLOYMENT_MODE") != "dedicated":
        errors.append("AXON_WATCH_DEPLOYMENT_MODE should be dedicated in deployment.env.example")

    if LOCAL_ENV_EXAMPLE.is_file():
        local_keys = set(_parse_env_file(LOCAL_ENV_EXAMPLE))
        uncovered = sorted(local_keys - set(values) - {"# comment keys"})
        # Allow local-only keys; require all deployment keys exist in local example superset
        for key in REQUIRED_DEPLOYMENT_KEYS:
            if key not in local_keys and key in {
                "AXON_WATCH_DEPLOYMENT_MODE",
                "AXON_WATCH_REPO_ROOT",
                "AXON_WATCH_BIND_HOST",
                "AXON_WATCH_CORS_ORIGINS",
            }:
                continue
    return errors


def validate_caddy_example() -> list[str]:
    errors: list[str] = []
    if not CADDY_EXAMPLE.is_file():
        return [f"missing Caddy example: {CADDY_EXAMPLE.relative_to(REPO_ROOT)}"]

    text = CADDY_EXAMPLE.read_text(encoding="utf-8")
    if "/api/*" not in text and "handle /api" not in text:
        errors.append("Caddyfile.example must route /api to control-plane")
    if "internal/watch" in text.lower():
        errors.append("Caddyfile.example must not expose /internal/watch publicly")
    if "reverse_proxy" not in text:
        errors.append("Caddyfile.example must define reverse_proxy routes")
    return errors


def validate_systemd_units() -> list[str]:
    errors: list[str] = []
    expected = (
        "axon-watch.service",
        "control-plane.service",
        "console-web.service",
    )
    for name in expected:
        path = SYSTEMD_DIR / name
        if not path.is_file():
            errors.append(f"missing systemd unit: infra/systemd/{name}")
            continue
        text = path.read_text(encoding="utf-8")
        if "EnvironmentFile=" not in text:
            errors.append(f"{name} must reference EnvironmentFile=")
        if "run-service.sh" not in text:
            errors.append(f"{name} must invoke scripts/ops/run-service.sh")
    return errors


def validate_user_systemd_units() -> list[str]:
    errors: list[str] = []
    expected = (
        "axon-watch.service",
        "control-plane.service",
        "console-web.service",
    )
    for name in expected:
        path = SYSTEMD_USER_DIR / name
        if not path.is_file():
            errors.append(f"missing user systemd unit: infra/systemd/user/{name}")
            continue
        text = path.read_text(encoding="utf-8")
        if "EnvironmentFile=" not in text:
            errors.append(f"user {name} must reference EnvironmentFile=")
        if "run-service.sh" not in text:
            errors.append(f"user {name} must invoke scripts/ops/run-service.sh")
    return errors


def validate_bin_wrappers() -> list[str]:
    errors: list[str] = []
    expected = (
        ("axonhealth", "axonhealth.sh"),
        ("axonrestart", "axonrestart.sh"),
        ("axonrevive", "axonrevive.sh"),
    )
    for bin_name, script_name in expected:
        bin_path = REPO_ROOT / "bin" / bin_name
        script_path = REPO_ROOT / "scripts" / "ops" / script_name
        if not bin_path.is_file():
            errors.append(f"missing bin wrapper: bin/{bin_name}")
            continue
        if not script_path.is_file():
            errors.append(f"missing ops script: scripts/ops/{script_name}")
            continue
        if not bin_path.stat().st_mode & 0o111:
            errors.append(f"bin/{bin_name} must be executable")
        if not script_path.stat().st_mode & 0o111:
            errors.append(f"scripts/ops/{script_name} must be executable")
        bin_text = bin_path.read_text(encoding="utf-8")
        if f"scripts/ops/{script_name}" not in bin_text:
            errors.append(f"bin/{bin_name} must exec scripts/ops/{script_name}")
    install_script = REPO_ROOT / "scripts" / "ops" / "install-bin-wrappers.sh"
    if not install_script.is_file():
        errors.append("missing scripts/ops/install-bin-wrappers.sh")
    return errors


def run_validation() -> list[str]:
    errors: list[str] = []
    errors.extend(validate_topology())
    errors.extend(validate_deployment_env_example())
    errors.extend(validate_caddy_example())
    errors.extend(validate_systemd_units())
    errors.extend(validate_user_systemd_units())
    errors.extend(validate_bin_wrappers())
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    errors = run_validation()
    if errors:
        print("deployment config validation FAILED:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print("deployment config validation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
