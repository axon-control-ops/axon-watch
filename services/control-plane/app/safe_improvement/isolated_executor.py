"""Isolated proposal workspace execution (never mutates bound workspace root)."""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4


def create_isolation_root(*, proposal_id: str) -> Path:
    root = Path(tempfile.mkdtemp(prefix=f"axon-si-{proposal_id[:12]}-"))
    (root / "MARKER").write_text("baseline\n", encoding="utf-8")
    (root / "metrics.json").write_text(
        json.dumps({"latency_ms": 100.0}, sort_keys=True),
        encoding="utf-8",
    )
    return root


def read_marker(root: Path) -> str:
    return (root / "MARKER").read_text(encoding="utf-8").strip()


def read_metric(root: Path, metric: str) -> float:
    payload = json.loads((root / "metrics.json").read_text(encoding="utf-8"))
    if metric not in payload:
        raise KeyError(f"metric `{metric}` missing in isolation root")
    return float(payload[metric])


def apply_candidate_change(
    root: Path,
    *,
    metric: str,
    candidate_value: float,
    marker: str = "candidate",
) -> dict[str, Any]:
    """Mutate only the isolated workspace; returns a change receipt."""
    metrics_path = root / "metrics.json"
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    before = float(payload.get(metric, 0.0))
    payload[metric] = float(candidate_value)
    metrics_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    (root / "MARKER").write_text(f"{marker}\n", encoding="utf-8")
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return {
        "receipt_id": f"iso_{uuid4().hex[:12]}",
        "kind": "isolated_candidate_change",
        "metric": metric,
        "before": before,
        "after": float(candidate_value),
        "marker": marker,
        "content_hash": f"sha256:{digest[:16]}",
        "isolation_root": str(root),
    }


def restore_baseline(root: Path, *, baseline_marker: str, baseline_metric_value: float, metric: str) -> dict[str, Any]:
    metrics_path = root / "metrics.json"
    payload = {metric: float(baseline_metric_value)}
    metrics_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    (root / "MARKER").write_text(f"{baseline_marker}\n", encoding="utf-8")
    return {
        "receipt_id": f"rb_{uuid4().hex[:12]}",
        "kind": "rollback",
        "metric": metric,
        "restored_value": float(baseline_metric_value),
        "restored_marker": baseline_marker,
        "isolation_root": str(root),
    }
