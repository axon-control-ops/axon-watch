"""Temporary runtime probes retained for the active Sentry debug session."""

from __future__ import annotations

import json
import time


def record_sentry_monitor_context(
    *,
    monitor_available: bool,
    status: str,
    issue_count: int,
) -> None:
    # region agent log
    try:
        with open(
            "/home/edp/axon-nvme/repos/axon-watch/.cursor/debug-fc0b35.log",
            "a",
            encoding="utf-8",
        ) as debug_log:
            debug_log.write(
                json.dumps(
                    {
                        "sessionId": "fc0b35",
                        "runId": "post-fix",
                        "hypothesisId": "SENTRY1",
                        "location": "cli_runtime/router.py:_sentry_monitor_context",
                        "message": "Sentry request received trusted monitor context",
                        "data": {
                            "monitorAvailable": monitor_available,
                            "status": status,
                            "issueCount": issue_count,
                        },
                        "timestamp": int(time.time() * 1000),
                    }
                )
                + "\n"
            )
    except OSError:
        pass
    # endregion


__all__ = ["record_sentry_monitor_context"]
