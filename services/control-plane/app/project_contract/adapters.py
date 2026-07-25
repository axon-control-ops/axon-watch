"""Stack adapters declared by project.axon.yaml."""

from __future__ import annotations

from typing import Any

ADAPTER_CAPABILITIES: dict[str, dict[str, Any]] = {
    "node_vue": {
        "languages": ["typescript", "javascript", "vue"],
        "package_managers": ["npm"],
        "default_checks": ["lint", "typecheck", "test", "build"],
    },
    "python_fastapi": {
        "languages": ["python"],
        "package_managers": ["pip"],
        "default_checks": ["test", "security", "diff_budget"],
    },
    "android_gradle": {
        "languages": ["kotlin", "java"],
        "package_managers": ["gradle"],
        "default_checks": ["lint", "test", "build"],
    },
}


def adapter_status(name: str) -> dict[str, Any]:
    caps = ADAPTER_CAPABILITIES.get(name)
    if caps is None:
        return {
            "adapter": name,
            "supported": False,
            "mode": "inspect_only",
            "capabilities": {},
        }
    return {
        "adapter": name,
        "supported": True,
        "mode": "certified",
        "capabilities": caps,
    }


def summarize_adapters(adapters: list[str]) -> list[dict[str, Any]]:
    return [adapter_status(name) for name in adapters]
