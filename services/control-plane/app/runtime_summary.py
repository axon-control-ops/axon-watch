"""Runtime summary entrypoint for the control-plane service."""

from __future__ import annotations

from app.runtime_summary_assembler import assemble_runtime_summary


def build_runtime_summary() -> dict[str, object]:
    return assemble_runtime_summary()
