#!/usr/bin/env python3
"""Idempotent backfill: Priya run_133bac → Lead synthesis → VAXON receipt.

Uses only verified fields from the stored specialist message and existing Dana
takeover. Does not invent Lead next, duplicate Dana takeover, or touch the
accidental services/control-plane/.local/state database.

Usage (from repo root):

  AXON_WATCH_CONTROL_PLANE_DB=/home/edp/axon-nvme/repos/axon-watch/.local/state/control-plane.sqlite3 \\
    python3 scripts/ops/backfill_priya_lead_vaxon_receipt.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTROL_PLANE_ROOT = REPO_ROOT / "services" / "control-plane"
LIVE_DB_DEFAULT = REPO_ROOT / ".local" / "state" / "control-plane.sqlite3"

RUN_ID = "run_133bac69735e"
WORKSPACE_ID = "workspace_dashpro"
SPECIALIST_MESSAGE_ID = "message_agent_d8ee9fb9fae64a6989804e91a193e721"
LEAD_MESSAGE_ID = "message_agent_63bf890a0c284feb9a28205420fa2bbd"

# Verbatim Lead-facing fields taken from the stored specialist report (not invented).
VERIFIED_LEAD_SUMMARY = (
    "Built the parent graduation confirm survey in the same card style as enrolment confirm."
)
VERIFIED_BLOCKERS = (
    "Marco: apply the new storage migration and seed/notify confirm rows "
    "(UI stays empty until those exist). Also owns unlocking the matching payment "
    "after a choice, and installment progress."
)
VERIFIED_LEAD_NEXT = (
    "decide when to run the parent notify campaign once storage is live."
)


def main() -> int:
    db_path = Path(os.environ.get("AXON_WATCH_CONTROL_PLANE_DB") or LIVE_DB_DEFAULT).resolve()
    accidental = (CONTROL_PLANE_ROOT / ".local" / "state" / "control-plane.sqlite3").resolve()
    if db_path == accidental:
        print("Refusing to write the accidental control-plane/.local/state database.", file=sys.stderr)
        return 2
    if not db_path.is_file():
        print(f"Database not found: {db_path}", file=sys.stderr)
        return 2

    os.environ["AXON_WATCH_CONTROL_PLANE_DB"] = str(db_path)
    sys.path.insert(0, str(CONTROL_PLANE_ROOT))

    from app.workspace_agents import lead_adhoc_receipt_store
    from app.workspace_agents.lead_vaxon_handoff import (
        publish_ad_hoc_synthesis_to_vaxon,
        record_ad_hoc_lead_synthesis,
    )

    import sqlite3

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    specialist_row = conn.execute(
        "SELECT message_id, run_id, content FROM chat_messages WHERE message_id = ?",
        (SPECIALIST_MESSAGE_ID,),
    ).fetchone()
    lead_row = conn.execute(
        "SELECT message_id, thread_id FROM chat_messages WHERE message_id = ?",
        (LEAD_MESSAGE_ID,),
    ).fetchone()
    conn.close()

    if specialist_row is None:
        print(f"Missing specialist message {SPECIALIST_MESSAGE_ID}", file=sys.stderr)
        return 2
    content = str(specialist_row["content"] or "")
    if VERIFIED_LEAD_SUMMARY.split(".")[0] not in content:
        print("Specialist message does not contain verified summary text.", file=sys.stderr)
        return 2
    if lead_row is None:
        print(f"Missing Dana takeover message {LEAD_MESSAGE_ID}", file=sys.stderr)
        return 2

    prior_vaxon = lead_adhoc_receipt_store.find_receipt_for_run(
        run_id=RUN_ID,
        kind=lead_adhoc_receipt_store.KIND_VAXON_POSTED,
    )
    if prior_vaxon is not None:
        print(
            {
                "status": "already_posted",
                "receipt_id": prior_vaxon.get("receipt_id"),
                "run_id": RUN_ID,
            }
        )
        return 0

    synthesis = record_ad_hoc_lead_synthesis(
        workspace_id=WORKSPACE_ID,
        run_id=RUN_ID,
        employee_role="frontend",
        employee_name="Priya",
        phase="completed",
        lead_next=VERIFIED_LEAD_NEXT,
        lead_summary=VERIFIED_LEAD_SUMMARY,
        lead_thread_id=str(lead_row["thread_id"]),
        lead_message_id=LEAD_MESSAGE_ID,
        blockers=VERIFIED_BLOCKERS,
    )
    published = publish_ad_hoc_synthesis_to_vaxon(
        workspace_id=WORKSPACE_ID,
        run_id=RUN_ID,
        synthesis_receipt_id=str(synthesis.get("receipt_id") or "") or None,
    )
    print(
        {
            "status": published.get("status"),
            "synthesis_status": synthesis.get("status"),
            "synthesis_receipt_id": synthesis.get("receipt_id"),
            "published": {
                "status": published.get("status"),
                "receipt_id": published.get("receipt_id"),
                "message_id": published.get("message_id"),
                "thread_id": published.get("thread_id"),
            },
            "db": str(db_path),
        }
    )
    return 0 if published.get("status") in {"posted", "already_posted"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
