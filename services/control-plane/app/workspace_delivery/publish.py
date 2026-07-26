"""Commit / push / draft-PR publish for worker isolation checkouts."""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.safe_improvement.isolated_executor import read_baseline_metadata
from app.workspace_agents.diff_policy import (
    evaluate_changed_paths,
    resolve_effective_allowed_paths,
    scan_text_for_secrets,
)
from app.workspace_delivery.config import (
    WorkspaceDeliveryPolicy,
    get_workspace_delivery_policy,
    is_protected_branch,
)
from app.workspace_delivery import store as delivery_store
from app.workspace_delivery.receipts import delivery_refs_from_record, emit_delivery_receipt

logger = logging.getLogger(__name__)

_GIT_TIMEOUT = 60
_GH_TIMEOUT = 90
_PROTECTED_PUSH_RE = re.compile(r"^(main|master|dev|production|release)$", re.IGNORECASE)


@dataclass(frozen=True)
class PublishResult:
    ok: bool
    stage: str
    delivery: dict[str, Any] | None
    detail: str
    cleanup_isolation: bool


def _run(
    args: list[str],
    *,
    cwd: Path,
    timeout: int = _GIT_TIMEOUT,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _combined(result: subprocess.CompletedProcess[str]) -> str:
    return "\n".join(
        part.strip() for part in (result.stdout, result.stderr) if part and part.strip()
    ).strip() or "(no output)"


def list_isolation_changed_paths(isolation_root: Path) -> list[str]:
    paths: list[str] = []
    for args in (
        ["git", "diff", "--name-only", "HEAD"],
        ["git", "diff", "--name-only", "--cached"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ):
        result = _run(args, cwd=isolation_root)
        if result.returncode != 0:
            continue
        for line in (result.stdout or "").splitlines():
            cleaned = line.strip()
            if cleaned and cleaned not in paths and not cleaned.startswith(".axon-si/"):
                paths.append(cleaned)
    return paths


def _derive_commit_message(paths: list[str], turn_subject: str | None) -> str:
    text = " ".join(str(turn_subject or "").split()).strip()
    if text and len(text) <= 72 and not text.endswith("?") and text[:1].isupper():
        return text
    if text and 8 <= len(text) <= 90 and not text.endswith("?"):
        cut = text[:71].rsplit(" ", 1)[0].rstrip(" ,.-")
        return f"{cut}…" if len(text) > 72 and cut else text[:72]
    if not paths:
        return "Worker delivery via Axon-X"
    basenames = [path.rsplit("/", 1)[-1] for path in paths[:2]]
    focus = ", ".join(basenames)
    if len(paths) > 2:
        focus = f"{focus} (+{len(paths) - 2} more)"
    subject = f"Update {focus}"
    return subject[:72]


def _task_allowed_paths(task_id: str | None) -> list[str]:
    key = str(task_id or "").strip()
    if not key:
        return []
    try:
        from app.persistence import task_store

        task = task_store.get_task(key)
    except Exception:  # noqa: BLE001 — publish must not crash on ledger read
        return []
    if not isinstance(task, dict):
        return []
    raw = task.get("allowed_paths")
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


def _contract_scope(isolation_root: Path) -> tuple[list[str], list[str]]:
    try:
        from app.workspace_agents.verifier_checks import load_repo_contract

        contract = load_repo_contract(str(isolation_root))
    except Exception:  # noqa: BLE001 — fall back to secret/forbidden defaults
        return [], [
            "**/.env",
            "**/.env.*",
            "**/id_rsa",
            "**/*secret*",
            "**/credentials.json",
        ]
    allowed = [
        str(item).strip()
        for item in (contract.get("allowed_paths") or [])
        if str(item).strip()
    ]
    forbidden = [
        str(item).strip()
        for item in (contract.get("forbidden_path_globs") or [])
        if str(item).strip()
    ]
    if not forbidden:
        forbidden = [
            "**/.env",
            "**/.env.*",
            "**/id_rsa",
            "**/*secret*",
            "**/credentials.json",
        ]
    return allowed, forbidden


def _scan_publish_scope(
    isolation_root: Path,
    paths: list[str],
    *,
    task_id: str | None,
) -> str | None:
    """Mirror Gate 6 path policy so publish cannot be looser than acceptance."""
    contract_allowed, forbidden = _contract_scope(isolation_root)
    effective = resolve_effective_allowed_paths(
        contract_allowed_paths=contract_allowed,
        task_allowed_paths=_task_allowed_paths(task_id),
    )
    findings = evaluate_changed_paths(
        paths,
        allowed_paths=effective,
        forbidden_path_globs=forbidden,
        max_paths=120,
    )
    if findings:
        first = findings[0]
        return f"{first.code}: {first.path} ({first.detail})"
    return None


def _scan_secrets(isolation_root: Path, paths: list[str]) -> str | None:
    findings = evaluate_changed_paths(
        paths,
        allowed_paths=[],
        forbidden_path_globs=[
            "**/.env",
            "**/.env.*",
            "**/id_rsa",
            "**/*secret*",
            "**/credentials.json",
        ],
        max_paths=120,
    )
    if findings:
        return findings[0].detail
    for path in paths[:40]:
        target = isolation_root / path
        if not target.is_file():
            continue
        try:
            text = target.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        hits = scan_text_for_secrets(text)
        if hits:
            return f"secret pattern in {path}"
    return None


def _ensure_not_protected(policy: WorkspaceDeliveryPolicy, branch: str) -> str | None:
    if is_protected_branch(policy, branch) or _PROTECTED_PUSH_RE.match(branch.strip()):
        return f"refusing to push protected branch {branch}"
    return None


def _open_or_update_draft_pr(
    *,
    isolation_root: Path,
    policy: WorkspaceDeliveryPolicy,
    worker_branch: str,
    title: str,
    body: str,
) -> tuple[bool, str]:
    if not shutil.which("gh"):
        return False, "gh CLI is required to open a draft PR"
    existing = _run(
        [
            "gh",
            "pr",
            "list",
            "--head",
            worker_branch,
            "--base",
            policy.base_branch,
            "--json",
            "url,isDraft",
            "--limit",
            "1",
        ],
        cwd=isolation_root,
        timeout=_GH_TIMEOUT,
    )
    if existing.returncode == 0 and existing.stdout.strip().startswith("["):
        try:
            import json

            rows = json.loads(existing.stdout)
        except json.JSONDecodeError:
            rows = []
        if isinstance(rows, list) and rows:
            url = str((rows[0] or {}).get("url") or "").strip()
            if url:
                return True, url
    created = _run(
        [
            "gh",
            "pr",
            "create",
            "--draft",
            "--base",
            policy.base_branch,
            "--head",
            worker_branch,
            "--title",
            title[:120],
            "--body",
            body[:4000] or "Worker delivery via Axon-X.",
        ],
        cwd=isolation_root,
        timeout=_GH_TIMEOUT,
    )
    output = _combined(created)
    if created.returncode != 0:
        return False, output
    url = ""
    for line in output.splitlines():
        if "github.com" in line and "/pull/" in line:
            url = line.strip()
            break
    return True, url or output


def publish_worker_isolation(
    *,
    workspace_id: str,
    run_id: str,
    isolation_root: Path,
    task_id: str | None = None,
    turn_subject: str | None = None,
) -> PublishResult:
    """Commit/push/draft-PR from a disposable worker isolation root."""
    policy = get_workspace_delivery_policy(workspace_id)
    if policy is None or not policy.enabled:
        return PublishResult(
            ok=True,
            stage="no_change",
            delivery=None,
            detail="workspace delivery disabled or unconfigured",
            cleanup_isolation=True,
        )
    if policy.push_policy != "draft_pr":
        return PublishResult(
            ok=False,
            stage="blocked",
            delivery=None,
            detail=f"unsupported push_policy={policy.push_policy}",
            cleanup_isolation=False,
        )

    try:
        meta = read_baseline_metadata(isolation_root)
    except Exception as exc:  # noqa: BLE001
        return PublishResult(
            ok=False,
            stage="blocked",
            delivery=None,
            detail=f"missing isolation metadata: {exc}",
            cleanup_isolation=False,
        )

    worker_branch = str(meta.get("worker_branch") or "").strip()
    baseline_sha = str(meta.get("baseline_commit") or "").strip()
    if not worker_branch:
        return PublishResult(
            ok=False,
            stage="blocked",
            delivery=None,
            detail="isolation metadata missing worker_branch",
            cleanup_isolation=False,
        )
    protected = _ensure_not_protected(policy, worker_branch)
    if protected:
        return PublishResult(
            ok=False,
            stage="blocked",
            delivery=None,
            detail=protected,
            cleanup_isolation=False,
        )

    paths = list_isolation_changed_paths(isolation_root)
    delivery = delivery_store.create_delivery(
        workspace_id=workspace_id,
        run_id=run_id,
        task_id=task_id,
        stage="changed" if paths else "no_change",
        baseline_sha=baseline_sha or None,
        worker_branch=worker_branch,
        isolation_root=str(isolation_root),
        attempt_budget=policy.attempt_budget,
        refs={"worker_branch": worker_branch, "baseline_sha": baseline_sha},
    )
    if not paths:
        emit_delivery_receipt(
            run_id,
            stage="no_change",
            summary="No publishable changes in worker isolation",
            refs=delivery_refs_from_record(delivery),
        )
        return PublishResult(
            ok=True,
            stage="no_change",
            delivery=delivery,
            detail="no changes",
            cleanup_isolation=True,
        )

    emit_delivery_receipt(
        run_id,
        stage="changed",
        summary=f"{len(paths)} changed path(s) ready for delivery",
        refs=delivery_refs_from_record(delivery),
    )

    scope_hit = _scan_publish_scope(isolation_root, paths, task_id=task_id)
    if scope_hit:
        delivery_store.update_delivery(
            str(delivery["delivery_id"]),
            stage="blocked",
            blocker=scope_hit,
            refs={"blocker": scope_hit},
        )
        emit_delivery_receipt(
            run_id,
            stage="blocked",
            summary=scope_hit,
            success=False,
            refs={"blocker": scope_hit, "worker_branch": worker_branch},
        )
        return PublishResult(
            ok=False,
            stage="blocked",
            delivery=delivery_store.get_delivery(str(delivery["delivery_id"])),
            detail=scope_hit,
            cleanup_isolation=False,
        )

    secret_hit = _scan_secrets(isolation_root, paths)
    if secret_hit:
        delivery_store.update_delivery(
            str(delivery["delivery_id"]),
            stage="blocked",
            blocker=secret_hit,
            refs={"blocker": secret_hit},
        )
        emit_delivery_receipt(
            run_id,
            stage="blocked",
            summary=secret_hit,
            success=False,
            refs={"blocker": secret_hit, "worker_branch": worker_branch},
        )
        return PublishResult(
            ok=False,
            stage="blocked",
            delivery=delivery_store.get_delivery(str(delivery["delivery_id"])),
            detail=secret_hit,
            cleanup_isolation=False,
        )

    message = _derive_commit_message(paths, turn_subject)
    staged = _run(["git", "add", "-A"], cwd=isolation_root)
    if staged.returncode != 0:
        detail = _combined(staged)
        delivery_store.update_delivery(
            str(delivery["delivery_id"]),
            stage="blocked",
            blocker=detail,
        )
        emit_delivery_receipt(
            run_id,
            stage="blocked",
            summary=f"git add failed: {detail}",
            success=False,
            refs={"worker_branch": worker_branch},
        )
        return PublishResult(
            ok=False,
            stage="blocked",
            delivery=delivery_store.get_delivery(str(delivery["delivery_id"])),
            detail=detail,
            cleanup_isolation=False,
        )

    # Drop sidecar-only noise from the commit when present.
    _run(["git", "reset", "HEAD", "--", ".axon-si"], cwd=isolation_root)
    committed = _run(["git", "commit", "-m", message], cwd=isolation_root)
    if committed.returncode != 0:
        detail = _combined(committed)
        if "nothing to commit" in detail.lower():
            delivery_store.update_delivery(str(delivery["delivery_id"]), stage="no_change")
            emit_delivery_receipt(
                run_id,
                stage="no_change",
                summary="Nothing to commit after staging",
                refs={"worker_branch": worker_branch},
            )
            return PublishResult(
                ok=True,
                stage="no_change",
                delivery=delivery_store.get_delivery(str(delivery["delivery_id"])),
                detail="nothing to commit",
                cleanup_isolation=True,
            )
        delivery_store.update_delivery(
            str(delivery["delivery_id"]),
            stage="blocked",
            blocker=detail,
        )
        emit_delivery_receipt(
            run_id,
            stage="blocked",
            summary=f"git commit failed: {detail}",
            success=False,
            refs={"worker_branch": worker_branch},
        )
        return PublishResult(
            ok=False,
            stage="blocked",
            delivery=delivery_store.get_delivery(str(delivery["delivery_id"])),
            detail=detail,
            cleanup_isolation=False,
        )

    sha_result = _run(["git", "rev-parse", "HEAD"], cwd=isolation_root)
    commit_sha = (sha_result.stdout or "").strip()
    delivery_store.update_delivery(
        str(delivery["delivery_id"]),
        stage="committed",
        commit_sha=commit_sha or None,
        clear_blocker=True,
        refs={"commit_sha": commit_sha, "worker_branch": worker_branch},
    )
    emit_delivery_receipt(
        run_id,
        stage="committed",
        summary=f"Committed: {message}",
        refs={"commit_sha": commit_sha, "worker_branch": worker_branch},
    )

    pushed = _run(
        ["git", "push", "-u", "origin", worker_branch],
        cwd=isolation_root,
        timeout=120,
    )
    if pushed.returncode != 0:
        detail = _combined(pushed)
        delivery_store.update_delivery(
            str(delivery["delivery_id"]),
            stage="blocked",
            blocker=detail,
        )
        emit_delivery_receipt(
            run_id,
            stage="blocked",
            summary=f"git push failed: {detail}",
            success=False,
            refs={"commit_sha": commit_sha, "worker_branch": worker_branch, "blocker": detail},
        )
        return PublishResult(
            ok=False,
            stage="blocked",
            delivery=delivery_store.get_delivery(str(delivery["delivery_id"])),
            detail=detail,
            cleanup_isolation=False,
        )

    delivery_store.update_delivery(str(delivery["delivery_id"]), stage="pushed")
    emit_delivery_receipt(
        run_id,
        stage="pushed",
        summary=f"Pushed {worker_branch}",
        refs={"commit_sha": commit_sha, "worker_branch": worker_branch},
    )

    pr_ok, pr_value = _open_or_update_draft_pr(
        isolation_root=isolation_root,
        policy=policy,
        worker_branch=worker_branch,
        title=message,
        body=(
            f"Automated worker delivery for run `{run_id}`.\n\n"
            f"- Branch: `{worker_branch}`\n"
            f"- Commit: `{commit_sha}`\n"
            f"- Paths: {len(paths)}\n"
        ),
    )
    if not pr_ok:
        delivery_store.update_delivery(
            str(delivery["delivery_id"]),
            stage="blocked",
            blocker=pr_value,
        )
        emit_delivery_receipt(
            run_id,
            stage="blocked",
            summary=f"draft PR failed: {pr_value}",
            success=False,
            refs={
                "commit_sha": commit_sha,
                "worker_branch": worker_branch,
                "blocker": pr_value,
            },
        )
        return PublishResult(
            ok=False,
            stage="blocked",
            delivery=delivery_store.get_delivery(str(delivery["delivery_id"])),
            detail=pr_value,
            cleanup_isolation=False,
        )

    delivery_store.update_delivery(
        str(delivery["delivery_id"]),
        stage="ci_pending",
        draft_pr_url=pr_value,
        clear_blocker=True,
        refs={"draft_pr_url": pr_value},
    )
    emit_delivery_receipt(
        run_id,
        stage="pr_open",
        summary=f"Draft PR ready: {pr_value}",
        refs={
            "draft_pr_url": pr_value,
            "commit_sha": commit_sha,
            "worker_branch": worker_branch,
        },
    )
    emit_delivery_receipt(
        run_id,
        stage="ci_pending",
        summary="Waiting for configured CI on the repair head",
        refs={
            "draft_pr_url": pr_value,
            "commit_sha": commit_sha,
            "worker_branch": worker_branch,
        },
    )
    return PublishResult(
        ok=True,
        stage="ci_pending",
        delivery=delivery_store.get_delivery(str(delivery["delivery_id"])),
        detail=pr_value,
        cleanup_isolation=True,
    )
