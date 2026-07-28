"""Temporary autonomy probes for debug session bef50e."""

from __future__ import annotations

import json
import time
from typing import Any


def debug_autonomy_probe(
    hypothesis_id: str,
    message: str,
    data: dict[str, Any],
) -> None:
    # region agent log
    payload = {
        "sessionId": "bef50e",
        "runId": "post-fix",
        "hypothesisId": hypothesis_id,
        "location": "workspace_agents/scheduler.py",
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    try:
        with open(
            "/home/edp/axon-nvme/repos/axon-watch/.cursor/debug-bef50e.log",
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
    except OSError:
        pass
    # endregion


__all__ = ["debug_autonomy_probe"]
