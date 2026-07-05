"""Rules for which canonical watch signals belong in the inbox snapshot."""

from __future__ import annotations


def connectors_trusted(records: list[dict[str, object]] | None) -> bool:
    """True when every required connector probe reports ok."""
    if not records:
        return False

    required = [record for record in records if record.get("required")]
    if not required:
        return False

    return all(str(record.get("status", "")).strip() == "ok" for record in required)


def include_summary_degraded_signal(
    *,
    connector_records: list[dict[str, object]] | None,
) -> bool:
    """Omit bootstrap summary-degraded noise once required connector truth is trusted."""
    return not connectors_trusted(connector_records)
