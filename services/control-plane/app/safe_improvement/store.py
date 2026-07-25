"""SQLite persistence for safe-improvement traces, cases, and proposals."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from collections.abc import Iterator
from typing import Any

from app.persistence import run_store_sqlite
from app.safe_improvement.models import (
    EffectApproval,
    EvaluationCase,
    ImprovementTrace,
    Proposal,
    VerificationResult,
)


def _configured_db_path() -> str | None:
    return os.environ.get("AXON_WATCH_CONTROL_PLANE_DB")


def ensure_safe_improvement_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS safe_improvement_traces (
            trace_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            source_ref TEXT NOT NULL,
            summary TEXT NOT NULL,
            receipt_refs_json TEXT NOT NULL,
            redacted_payload_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS safe_improvement_cases (
            case_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            metric TEXT NOT NULL,
            threshold REAL NOT NULL,
            comparator TEXT NOT NULL,
            baseline_value REAL
        );

        CREATE TABLE IF NOT EXISTS safe_improvement_proposals (
            proposal_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            trace_id TEXT NOT NULL,
            case_id TEXT NOT NULL,
            status TEXT NOT NULL,
            effect_kind TEXT NOT NULL,
            title TEXT NOT NULL,
            isolation_root TEXT,
            baseline_commit TEXT,
            baseline_marker TEXT,
            candidate_marker TEXT,
            verification_json TEXT,
            effect_fingerprint TEXT,
            approval_json TEXT,
            receipts_json TEXT NOT NULL,
            error TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_safe_improvement_proposals_created
            ON safe_improvement_proposals(created_at DESC);
        """
    )
    _ensure_column(
        connection,
        "safe_improvement_proposals",
        "baseline_commit",
        "TEXT",
    )


def _ensure_column(
    connection: sqlite3.Connection,
    table: str,
    column: str,
    column_type: str,
) -> None:
    existing = {
        str(row["name"])
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in existing:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")


@contextmanager
def _connection() -> Iterator[sqlite3.Connection]:
    connection = run_store_sqlite.connect(_configured_db_path())
    try:
        ensure_safe_improvement_schema(connection)
        yield connection
        connection.commit()
    finally:
        connection.close()


def save_trace(trace: ImprovementTrace) -> ImprovementTrace:
    with _connection() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO safe_improvement_traces (
                trace_id, created_at, workspace_id, source_kind, source_ref,
                summary, receipt_refs_json, redacted_payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trace.trace_id,
                trace.created_at,
                trace.workspace_id,
                trace.source_kind,
                trace.source_ref,
                trace.summary,
                json.dumps(list(trace.receipt_refs)),
                json.dumps(trace.redacted_payload),
            ),
        )
    return trace


def get_trace(trace_id: str) -> ImprovementTrace | None:
    with _connection() as connection:
        row = connection.execute(
            "SELECT * FROM safe_improvement_traces WHERE trace_id = ?",
            (trace_id,),
        ).fetchone()
    if row is None:
        return None
    return ImprovementTrace(
        trace_id=row["trace_id"],
        created_at=row["created_at"],
        workspace_id=row["workspace_id"],
        source_kind=row["source_kind"],
        source_ref=row["source_ref"],
        summary=row["summary"],
        receipt_refs=tuple(json.loads(row["receipt_refs_json"] or "[]")),
        redacted_payload=json.loads(row["redacted_payload_json"] or "{}"),
    )


def save_case(case: EvaluationCase) -> EvaluationCase:
    with _connection() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO safe_improvement_cases (
                case_id, name, metric, threshold, comparator, baseline_value
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                case.case_id,
                case.name,
                case.metric,
                case.threshold,
                case.comparator,
                case.baseline_value,
            ),
        )
    return case


def get_case(case_id: str) -> EvaluationCase | None:
    with _connection() as connection:
        row = connection.execute(
            "SELECT * FROM safe_improvement_cases WHERE case_id = ?",
            (case_id,),
        ).fetchone()
    if row is None:
        return None
    return EvaluationCase(
        case_id=row["case_id"],
        name=row["name"],
        metric=row["metric"],
        threshold=float(row["threshold"]),
        comparator=row["comparator"],
        baseline_value=(
            None if row["baseline_value"] is None else float(row["baseline_value"])
        ),
    )


def _proposal_from_row(row: sqlite3.Row) -> Proposal:
    verification_raw = row["verification_json"]
    approval_raw = row["approval_json"]
    verification = None
    if verification_raw:
        verification = VerificationResult(**json.loads(verification_raw))
    approval = None
    if approval_raw:
        approval = EffectApproval(**json.loads(approval_raw))
    return Proposal(
        proposal_id=row["proposal_id"],
        created_at=row["created_at"],
        workspace_id=row["workspace_id"],
        trace_id=row["trace_id"],
        case_id=row["case_id"],
        status=row["status"],
        effect_kind=row["effect_kind"],
        title=row["title"],
        isolation_root=row["isolation_root"],
        baseline_commit=row["baseline_commit"] if "baseline_commit" in row.keys() else None,
        baseline_marker=row["baseline_marker"],
        candidate_marker=row["candidate_marker"],
        verification=verification,
        effect_fingerprint=row["effect_fingerprint"],
        approval=approval,
        receipts=json.loads(row["receipts_json"] or "[]"),
        error=row["error"],
    )


def save_proposal(proposal: Proposal) -> Proposal:
    with _connection() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO safe_improvement_proposals (
                proposal_id, created_at, workspace_id, trace_id, case_id, status,
                effect_kind, title, isolation_root, baseline_commit, baseline_marker,
                candidate_marker, verification_json, effect_fingerprint, approval_json,
                receipts_json, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                proposal.proposal_id,
                proposal.created_at,
                proposal.workspace_id,
                proposal.trace_id,
                proposal.case_id,
                proposal.status,
                proposal.effect_kind,
                proposal.title,
                proposal.isolation_root,
                proposal.baseline_commit,
                proposal.baseline_marker,
                proposal.candidate_marker,
                (
                    json.dumps(proposal.verification.to_dict())
                    if proposal.verification
                    else None
                ),
                proposal.effect_fingerprint,
                json.dumps(proposal.approval.to_dict()) if proposal.approval else None,
                json.dumps(proposal.receipts),
                proposal.error,
            ),
        )
    return proposal


def get_proposal(proposal_id: str) -> Proposal | None:
    with _connection() as connection:
        row = connection.execute(
            "SELECT * FROM safe_improvement_proposals WHERE proposal_id = ?",
            (proposal_id,),
        ).fetchone()
    if row is None:
        return None
    return _proposal_from_row(row)


def list_proposals(*, limit: int = 20) -> list[dict[str, Any]]:
    with _connection() as connection:
        rows = connection.execute(
            """
            SELECT * FROM safe_improvement_proposals
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (max(1, min(int(limit), 100)),),
        ).fetchall()
    return [_proposal_from_row(row).to_dict() for row in rows]
