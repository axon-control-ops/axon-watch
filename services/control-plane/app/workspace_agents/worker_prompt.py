"""Role-scoped prompts for continuous employee-agent shifts."""

from __future__ import annotations

import re
from typing import Any

from app.workspace_agents.catalog import _DEFAULT_OWNS
from app.workspace_agents.config_loader import EmployeeConfig
from app.workspace_agents.critical_review_clause import append_critical_review_clause
from app.workspace_agents.employee_persona_prompt import build_employee_identity_line
from app.workspace_agents.lead_text import truncate_text as _truncate
from app.workspace_agents.run_outcome import latest_role_run_outcome
from app.workspace_agents.team_roster_context import build_team_roster_context

OUT_OF_SCOPE_GUARD_MARKER = "OUT_OF_SCOPE_GUARD:"
_OUT_OF_SCOPE_GUARD_RE = re.compile(r"OUT_OF_SCOPE_GUARD:\s*(.+)", re.IGNORECASE)


def _prior_failure_clause(*, workspace_id: str, role: str) -> str:
    """Surface the last terminal failure so a new shift can retry with context."""
    outcome = latest_role_run_outcome(workspace_id, role)
    if not outcome or str(outcome.get("outcome") or "").strip().lower() != "failed":
        return ""
    detail = str(outcome.get("detail") or "").strip()
    run_id = str(outcome.get("run_id") or "").strip()
    if not detail:
        detail = "open run history for receipts"
    run_hint = f" (run {run_id})" if run_id else ""
    return (
        f" Prior shift failed{run_hint}: {detail}. "
        "Prefer fixing or clearing that failure before unrelated work. "
    )


def _auto_mode_ask_clause() -> str:
    return (
        " Auto-mode question discipline: do not stop on ask cards for safe, "
        "reversible engineering choices such as continuing investigation, clearing "
        "local cache, hardening a route, or running targeted checks. Pick the safest "
        "progress path yourself, state the assumption, and continue. Only emit an "
        "Axon ask card for a real operator decision: destructive data changes, "
        "credentials/secrets, spending/billing, production release/merge/push, or an "
        "irreversible product choice."
    )


def _role_tools_clause(role: str) -> str:
    """Tell specialists which tools they should use — Full Access means Shell/Edit/Read."""
    cleaned = str(role or "").strip().lower()
    shared = (
        " Tools: this shift has Full Access for project Shell, Read, Edit, and Grep. "
        "Use them to verify — do not invent counts or claim done without a command receipt. "
        "If Shell fails once, retry once with a shorter command; then report the exact error. "
        "Do not spin on Task/MCP workarounds for basic ls/node/npm checks. "
    )
    if cleaned == "watcher":
        return (
            shared
            + "Watcher focus: health probes, signal receipts, and CI/gate status checks "
            "via short shell/read — not product feature builds. "
        )
    if cleaned == "integrations":
        return (
            shared
            + "Integrations focus: connector/export/linkage wiring plus verification scripts "
            "(node/npm smoke) with receipts before handoff. "
        )
    if cleaned == "backend":
        return (
            shared
            + "Backend focus: data/API/scripts with verified query or script output — "
            "not UI layout work. "
        )
    if cleaned == "frontend":
        return (
            shared
            + "Frontend focus: UI/files edits with targeted checks; avoid heavy servers "
            "unless the leased goal requires them. "
        )
    if cleaned == "lead":
        return (
            " Tools: prefer Read/ Grep for receipts and specialist reports; "
            "delegate Shell-heavy verification to specialists unless you must confirm a gate. "
        )
    return shared


def _task_scope_anchors(*parts: str, limit: int = 8) -> list[str]:
    anchors: list[str] = []
    seen: set[str] = set()
    for part in parts:
        text = str(part or "")
        candidates = re.findall(r"`([^`]+)`", text)
        candidates.extend(re.findall(r"\b[\w./-]*[./_-][\w./-]+\b", text))
        for raw in candidates:
            cleaned = str(raw).strip().strip(".,;:()[]{}")
            if not cleaned or len(cleaned) < 3:
                continue
            lowered = cleaned.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            anchors.append(cleaned)
            if len(anchors) >= limit:
                return anchors
    return anchors


def _task_scope_clause(
    *,
    goal: str,
    acceptance: str,
    allowed_paths: list[str] | None = None,
) -> str:
    paths = [str(p).strip() for p in (allowed_paths or []) if str(p).strip()]
    anchors = _task_scope_anchors(goal, acceptance)
    anchor_clause = ""
    if paths:
        joined = ", ".join(f"`{path}`" for path in paths[:12])
        anchor_clause = (
            f" Explicit allowed write paths for this leased task: {joined}. "
            "Do not modify any path outside that allowlist."
        )
    elif anchors:
        joined = ", ".join(f"`{anchor}`" for anchor in anchors)
        anchor_clause = f" Hard scope anchors from the task: {joined}. "
    return (
        " Scope guard: before you browse, edit, or summarize anything, lock onto the "
        "leased task's exact goal and acceptance criteria."
        f"{anchor_clause}"
        "Only open, mention, or modify files and topics that directly serve that scope. "
        "Do not drift into neighboring files, similarly named campaigns, prior tasks, or "
        "semantically related artifacts just because they are nearby. "
        "If the goal is about a README, docs, layout, bug, API, or specific deliverable, "
        "treat unrelated posts, assets, illustrations, marketing copy, and old workspace "
        "tasks as out of scope unless the goal explicitly asks for them. "
        f"If the next file or topic is not clearly justified by the task, stop and reply "
        f"with `{OUT_OF_SCOPE_GUARD_MARKER} <file-or-topic> is not required for this leased task` "
        "instead of continuing."
    )


def _current_task_packet(
    *,
    workspace_id: str,
    task_id: str,
    goal: str,
    acceptance: str,
    allowed_paths: list[str],
) -> str:
    expected = ", ".join(f"`{path}`" for path in allowed_paths[:12]) or "role/task scoped files"
    return (
        " Current task packet (authoritative; ignore stale thread context): "
        f"workspace=`{workspace_id.strip() or 'unknown'}`; "
        f"task_id=`{task_id}`; "
        f"title=`{_truncate(goal, max_len=90)}`; "
        f"objective=`{_truncate(goal, max_len=260)}`; "
        f"acceptance=`{_truncate(acceptance or 'Use receipts to prove the goal is met.', max_len=260)}`; "
        f"expected_files={expected}. "
        "If any prior conversation, previous run, tab title, or last-failure hint conflicts "
        "with this packet, this packet wins."
    )


def parse_out_of_scope_guard(reply_text: str) -> str | None:
    match = _OUT_OF_SCOPE_GUARD_RE.search(str(reply_text or ""))
    if match is None:
        return None
    detail = " ".join(match.group(1).split()).strip()
    return detail or "out-of-scope guard triggered"


def _lead_plan_evidence_clause(
    *,
    workspace_id: str,
    goal: str,
    acceptance: str,
    task_id: str,
) -> str:
    """Embed durable Lead-plan receipts into Lead worker prompts.

    Lead follow-up shifts often run in disposable checkouts that cannot read the
    live control-plane sqlite database. If the prompt only says "advance plan X",
    the Lead must either hallucinate status or block. This packet gives the Lead
    the minimal, sanitized control-plane truth needed to choose the next handoff.
    """
    try:
        from app.workspace_agents import lead_plan_store
        from app.workspace_agents.lead_plan_control import extract_plan_id_from_goal
    except Exception:  # noqa: BLE001
        return ""

    plan_id = (
        extract_plan_id_from_goal(goal)
        or extract_plan_id_from_goal(acceptance)
        or lead_plan_store.plan_id_for_task(task_id)
        or ""
    )
    plan_id = str(plan_id or "").strip()
    if not plan_id:
        return ""

    try:
        plan = lead_plan_store.get_plan(plan_id)
    except Exception:  # noqa: BLE001
        plan = None
    if not isinstance(plan, dict):
        return (
            " Lead plan evidence packet: the leased task references "
            f"{plan_id}, but this control-plane session has no durable Lead plan "
            "record for that id. Do not queue a self-follow-up that repeats the "
            "same blocker; report to VAXON/operator that the plan ledger is missing "
            "or stale and include the plan id."
        )
    if str(plan.get("workspace_id") or "").strip() != str(workspace_id or "").strip():
        return (
            " Lead plan evidence packet: the referenced plan belongs to a different "
            "workspace than this leased task. Stop and report the workspace mismatch "
            "to VAXON/operator with the plan id; do not invent a handoff."
        )

    plan_body = plan.get("plan") if isinstance(plan.get("plan"), dict) else {}
    items = plan_body.get("items") if isinstance(plan_body.get("items"), list) else []
    try:
        links = lead_plan_store.plan_task_links(plan_id)
    except Exception:  # noqa: BLE001
        links = []
    link_by_key = {
        str(link.get("plan_key") or "").strip(): str(link.get("task_id") or "").strip()
        for link in links
        if isinstance(link, dict)
    }
    lines = [
        " Lead plan evidence packet (control-plane truth for this disposable shift):",
        f"- Plan: {plan_id} | status={str(plan.get('status') or 'unknown')} | goal={_truncate(str(plan.get('goal') or ''), max_len=180)}",
    ]
    try:
        from app.persistence import task_store

        for index, item in enumerate(items[:8], start=1):
            if not isinstance(item, dict):
                continue
            plan_key = str(item.get("id") or item.get("plan_key") or f"plan-{index:02d}").strip()
            role = str(item.get("owner_role") or item.get("role") or "specialist").strip()
            title = _truncate(
                str(item.get("title") or item.get("goal") or item.get("summary") or ""),
                max_len=130,
            )
            linked_task_id = link_by_key.get(plan_key, "")
            status = "unlinked"
            run_id = ""
            if linked_task_id:
                row = task_store.get_task(linked_task_id)
                if isinstance(row, dict):
                    status = str(row.get("status") or "unknown").strip() or "unknown"
                    run_id = str(row.get("run_id") or "").strip()
            run_bit = f" run={run_id}" if run_id else ""
            task_bit = f" task={linked_task_id}" if linked_task_id else " task=unlinked"
            lines.append(f"- {plan_key}: {role} {status}{task_bit}{run_bit} — {title}")
    except Exception:  # noqa: BLE001
        lines.append("- Task-link status unavailable in this prompt; use receipts below.")

    try:
        receipts = lead_plan_store.list_receipts(plan_id)[-6:]
    except Exception:  # noqa: BLE001
        receipts = []
    if receipts:
        lines.append("- Recent receipts:")
        for receipt in receipts:
            if not isinstance(receipt, dict):
                continue
            payload = receipt.get("payload") if isinstance(receipt.get("payload"), dict) else {}
            summary = (
                payload.get("summary")
                or payload.get("status")
                or payload.get("goal")
                or payload.get("phase")
                or payload.get("run_id")
                or ""
            )
            lines.append(
                f"  - {str(receipt.get('kind') or 'receipt')}: "
                f"{_truncate(str(summary or ''), max_len=160)}"
            )
    lines.append(
        "- Use this packet as the verified baseline; advance the parent plan by choosing "
        "assign / ship / escalate / report, and cite task/run receipts when available."
    )
    return "\n".join(lines)


def build_continuous_worker_prompt(
    *,
    workspace_id: str,
    employee: EmployeeConfig,
    task: dict[str, Any] | None = None,
) -> str:
    role = str(employee.role or "").strip().lower() or "workspace_agent"
    owns = str(employee.owns or "").strip() or _DEFAULT_OWNS.get(role, "assigned workspace work")
    name = str(employee.name or role).strip() or role
    schedule = str(employee.schedule or "continuous").strip().lower()
    identity = build_employee_identity_line(
        workspace_id=workspace_id,
        name=name,
        role=role,
        owns=owns,
    )
    task_payload = task if isinstance(task, dict) else {}
    task_id = str(task_payload.get("task_id") or "").strip() or "task-unspecified"
    goal = str(task_payload.get("goal") or "").strip() or "Complete the leased task"
    acceptance = str(task_payload.get("acceptance_criteria") or "").strip()
    acceptance_clause = (
        f" Acceptance criteria: {acceptance}."
        if acceptance
        else " Use receipts to prove the goal is met."
    )
    allowed_paths_raw = task_payload.get("allowed_paths")
    allowed_paths = (
        [str(item).strip() for item in allowed_paths_raw if str(item).strip()]
        if isinstance(allowed_paths_raw, list)
        else []
    )
    scope_clause = _task_scope_clause(
        goal=goal,
        acceptance=acceptance,
        allowed_paths=allowed_paths,
    )
    ci_clause = ""
    if role in {"watcher", "backend", "integrations"}:
        ci_clause = (
            " If git/working-tree or open PR changes are in your scope: "
            "after the Critical Review Clause rewrite, run local verify "
            "(`npm run verify:contracts` and targeted tests) and report the real "
            "command output. "
            "Never report FAILED without the exact failing check, file, and error text. "
        )
    if workspace_id.strip() == "workspace_axon_watch" and role in {"watcher", "integrations", "lead"}:
        ci_clause += (
            " After any push to origin for this repo, poll Axon-X Fast Gate "
            "(`./scripts/ops/watch-fast-gate.sh` or `gh run watch`) and report the "
            "run URL + conclusion. Fix file-size ratchet failures via "
            "`scripts/guardrails/hotspot_budgets.json` or extraction — do not ignore red CI. "
        )
    if workspace_id.strip() == "workspace_dashpro" and role in {
        "watcher",
        "backend",
        "integrations",
        "lead",
    }:
        ci_clause += (
            " DashPro CI policy (operator-locked): all `.github/workflows/*` must use "
            "`runs-on: self-hosted` (runner label includes self-hosted / dashpro). "
            "Never switch jobs back to `ubuntu-latest` or other GitHub-hosted runners — "
            "hosted minutes are billing-blocked and fail in seconds while the self-hosted "
            "runner sits idle. On red/queued CI: check `gh run view` + "
            "`gh api repos/{owner}/{repo}/actions/runners` for runner online/busy; "
            "fix workflow YAML / secrets / self-hosted capacity — do not thrash hosted CI. "
        )
    goal_l = goal.lower()
    if "ci repair:" in goal_l or "gate 9" in goal_l or "fast gate" in goal_l:
        ci_clause += (
            " This leased task is a Gate 9 CI remediation. "
            "1) `gh run view <run_id> --log-failed` for the first hard-fail step. "
            "2) Apply the smallest fix (ratchet/extract/type). "
            "3) Commit and open/update a draft PR (push_policy=draft_pr); "
            "never force-push or merge protected branches. "
            "4) Re-watch the exact workflow on the repair head. "
            "5) POST JSON to "
            "`http://127.0.0.1:8787/api/ci-remediation/report-outcome` with the "
            "dedupe_key from the task goal, workspace_id, workflow_name, head_branch, "
            "success true/false, detail, html_url, and draft_pr_url. Include "
            "`Authorization: Bearer $AXON_WATCH_OPERATOR_TOKEN` when configured. "
            "Report spoken-ready outcome for the unaware operator. "
        )
    if "vaxon fleet repair" in goal_l:
        ci_clause += (
            " This leased task is a VAXON fleet self-heal repair — the bug is in "
            "axon-watch's own control-plane code, not this workspace's product code. "
            "Root-cause it (do not symptom-patch), add a regression test under tests/, "
            "push to a throwaway branch and open a draft PR, then confirm a green "
            "Axon-X Fast Gate run on that head before reporting success. "
            "POST JSON to `http://127.0.0.1:8787/api/fleet-self-heal/report-outcome` "
            "with fingerprint (from the task goal), success true/false, commit_ref "
            "(the fix commit sha or PR URL), and detail. Include "
            "`Authorization: Bearer $AXON_WATCH_OPERATOR_TOKEN` when configured. "
            "Report spoken-ready outcome for the unaware operator. "
        )
    memory_clause = (
        " Memory safety: do NOT start DashPro `web:dev` / Expo / Metro / "
        "`typecheck` with large NODE_OPTIONS heaps unless the operator explicitly asked. "
        "Prefer editing + targeted tests. Never launch a second heavy server if one is "
        "already listening. Axon-X operator UI is :4173 — do not start legacy :7734. "
        "Long-running OTA/Expo/EAS jobs: do not block on Cursor shellToolCall for the heavy "
        "job — bare `npm run ota:canary` / `eas update` in Cursor shell orphans the ship if "
        "Axon stale-fails the run. Start once via `axon-agent-terminal-job --workspace "
        f"{workspace_id.strip() or '<workspace_id>'} -- <command>` (PATH helper; not a "
        "relative DashPro path) so live output can stream into chat + vaxon. "
        "Disposable worker checkouts may intentionally lack usable `.git` metadata; "
        "do not treat `fatal: not a git repository` in the disposable checkout as proof "
        "that the real workspace is missing. The helper resolves the real workspace by "
        "`--workspace`; enqueue it once and let the real-workspace command perform its "
        "own branch, dirty-tree, and auth guards. If chat streaming is unavailable or "
        "stale, retry the helper with `--no-stream` rather than blocking the dispatch. "
        "After enqueue, poll "
        "`axon-agent-terminal-job --status <job_id> --workspace "
        f"{workspace_id.strip() or '<workspace_id>'}` sparsely (~30–60s), not busy-poll loops. "
        "Close with the Expo Updates branch/group receipt (operator-canary), not an EAS Build URL. "
    )
    if workspace_id.strip() == "workspace_dashpro":
        memory_clause += (
            " Temporary self-hosted CI on this PC: prefer "
            "`npm run ops:agents:quality` (subset) with "
            "`DASHPRO_CI_MEMORY_PROFILE=self-hosted` / Jest maxWorkers=1. "
            "Never run `ops:agents:quality:full`, Android CI, or parallel workflow_dispatch "
            "while Cursor is open — the local runner is MemoryMax-capped at 10G and previously "
            "OOM-froze the host at ~18G. Create/queue CI repair tasks for operator Start; "
            "do not stack Quality Gates + Android + typecheck heaps. "
        )
    prior_failure = "" if task_payload else _prior_failure_clause(workspace_id=workspace_id, role=role)
    task_packet = _current_task_packet(
        workspace_id=workspace_id,
        task_id=task_id,
        goal=goal,
        acceptance=acceptance,
        allowed_paths=allowed_paths,
    )
    roster_block = build_team_roster_context(workspace_id, viewer_role=role)
    roster_clause = f"\n\n{roster_block}" if roster_block else ""
    lead_clause = ""
    if role == "lead":
        lead_clause = (
            " As Lead, treat the company team roster block as authoritative for "
            "teammates, roles, and owns — do not Glob/Grep/Read the tree to discover "
            "staffing before planning or delegating."
            " Reporting chain: specialists → you → VAXON → operator Decide."
            " For frontend implementation assignments, act as coordinator/QA only: "
            "delegate the current task packet to the frontend specialist, then verify "
            "their actual diff, validation receipts, and delivery commit before reporting success."
            " After specialist completions, post a short Lead rollup (done / verified / next)."
        )
        if "[plan " in goal.lower() or goal.lower().startswith("lead: advance"):
            lead_clause += (
                " Parent-plan stickiness: the parent plan goal in this leased task is the "
                "sole completion criteria. Specialist digs and CI findings are inputs — "
                "do not restart a completed dig as the mission. Advance the plan; "
                "escalate Decide for ship gates."
            )
            lead_clause += _lead_plan_evidence_clause(
                workspace_id=workspace_id,
                goal=goal,
                acceptance=acceptance,
                task_id=task_id,
            )
    else:
        lead_clause = (
            " Reporting chain: finish with a Lead handoff (what changed, verified, "
            "Blockers / Lead next). Do not escalate straight to the operator — Lead owns that."
        )
    delivery_clause = (
        " Delivery discipline: work only in this disposable checkout. Before handoff, "
        "inspect the exact files you changed and report their paths plus the targeted checks "
        "you actually ran. Do not run `git add -A`, commit, push, merge, force-push, or "
        "touch a protected branch yourself. The delivery service independently checks scope "
        "and secrets, stages only your verified changed paths, then creates the worker-branch "
        "commit and draft PR. If any changed path is outside the leased task, stop and report "
        "it as a blocker instead of trying to include or discard it."
    )
    tools_clause = _role_tools_clause(role)
    return append_critical_review_clause(
        f"{identity} "
        f"This is a bounded continuous shift ({schedule}) for leased task {task_id}. "
        f"{prior_failure}"
        f"Execute only this leased task — do not invent, assume, or self-select other work. "
        f"The leased goal is the sole truth for this shift's scope. "
        f"{task_packet}"
        f"Goal: {goal}.{acceptance_clause} "
        "Do it with verified receipts and summarize what changed. "
        "Stay inside your role boundary. Never hallucinate outcomes."
        f"{scope_clause}"
        f"{lead_clause}"
        f"{delivery_clause}"
        f"{tools_clause}"
        f"{ci_clause}"
        f"{memory_clause}"
        f"{_auto_mode_ask_clause()}"
        " If a step fails, say what failed and why (command, assertion, import, CI step) — "
        "never a bare FAILED."
        f"{roster_clause}"
    )
