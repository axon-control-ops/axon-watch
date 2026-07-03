from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "scripts" / "verify" / "verification_config.json"


@dataclass
class CheckResult:
    name: str
    status: str
    message: str
    details: list[str] = field(default_factory=list)


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def percentile_95(samples: Sequence[float]) -> float:
    if not samples:
        raise ValueError("at least one sample is required")
    ordered = sorted(float(sample) for sample in samples)
    index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    return ordered[index]


def resolve_optional_path(cli_value: str | None, env_name: str | None) -> Path | None:
    candidate = cli_value
    if not candidate and env_name:
        candidate = Path.cwd().joinpath().as_posix()
        candidate = None
    if not candidate and env_name:
        import os

        candidate = os.environ.get(env_name)
    if not candidate:
        return None
    path = Path(candidate)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def compact_json_size_bytes(path: Path) -> int:
    payload = load_json(path)
    encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    return len(encoded)


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def emit(result: CheckResult) -> int:
    print(f"{result.status.upper()} {result.name}: {result.message}")
    for detail in result.details:
        print(f"  - {detail}")
    return 1 if result.status == "fail" else 0


def emit_many(results: Sequence[CheckResult]) -> int:
    exit_code = 0
    for result in results:
        exit_code = max(exit_code, emit(result))
    return exit_code
