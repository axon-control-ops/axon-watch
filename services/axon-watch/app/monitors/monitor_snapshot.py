"""Monitor probe snapshot for operator diagnostics (OP-B4)."""

from __future__ import annotations

from app.monitors.dashpro_monitor import probe_monitor_records
from app.signals.iso_time import utc_now_iso


def build_monitors_response() -> dict[str, object]:
    records = probe_monitor_records()
    ok_count = sum(1 for record in records if record.get("status") == "ok")
    skipped_count = sum(1 for record in records if record.get("status") == "skipped")
    warning_count = sum(1 for record in records if record.get("status") == "warning")
    critical_count = sum(1 for record in records if record.get("status") == "critical")
    live_signal_count = warning_count + critical_count

    return {
        "items": records,
        "count": len(records),
        "summary": {
            "ok": ok_count,
            "skipped": skipped_count,
            "warning": warning_count,
            "critical": critical_count,
            "live_signal_count": live_signal_count,
        },
        "updated_at": utc_now_iso(),
    }
