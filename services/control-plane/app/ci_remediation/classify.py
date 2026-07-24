"""Classify GitHub workflow_run payloads for Gate 9 ingest."""

from __future__ import annotations

from typing import Any


def classify_workflow_run_event(payload: dict[str, Any]) -> dict[str, str] | None:
    """
    Return normalized failure fields, or None when the event is not a
    completed workflow failure we should remediate.
    """
    action = str(payload.get("action") or "").strip().lower()
    run = payload.get("workflow_run")
    if not isinstance(run, dict):
        return None
    conclusion = str(run.get("conclusion") or "").strip().lower()
    status = str(run.get("status") or "").strip().lower()
    if action and action != "completed":
        return None
    if status and status != "completed":
        return None
    if conclusion != "failure":
        return None

    repo = payload.get("repository")
    owner = ""
    repo_name = ""
    if isinstance(repo, dict):
        repo_name = str(repo.get("name") or "").strip()
        owner_obj = repo.get("owner")
        if isinstance(owner_obj, dict):
            owner = str(owner_obj.get("login") or "").strip()
        full_name = str(repo.get("full_name") or "").strip()
        if not owner and "/" in full_name:
            owner, repo_name = full_name.split("/", 1)

    workflow_name = str(run.get("name") or "").strip()
    head_branch = str(run.get("head_branch") or "").strip()
    head_sha = str(run.get("head_sha") or "").strip()
    run_id = str(run.get("id") or "").strip()
    html_url = str(run.get("html_url") or "").strip()
    display_title = str(run.get("display_title") or run.get("name") or "").strip()

    if not owner or not repo_name or not workflow_name or not run_id:
        return None

    failing_step = _guess_failing_step(payload, run)
    return {
        "github_owner": owner,
        "github_repo": repo_name,
        "workflow_name": workflow_name,
        "head_branch": head_branch,
        "head_sha": head_sha,
        "run_id": run_id,
        "html_url": html_url,
        "display_title": display_title,
        "failing_step": failing_step,
        "conclusion": conclusion,
    }


def _guess_failing_step(payload: dict[str, Any], run: dict[str, Any]) -> str:
    jobs = payload.get("jobs")
    if isinstance(jobs, list):
        for job in jobs:
            if not isinstance(job, dict):
                continue
            if str(job.get("conclusion") or "").strip().lower() != "failure":
                continue
            name = str(job.get("name") or "").strip()
            steps = job.get("steps")
            if isinstance(steps, list):
                for step in steps:
                    if not isinstance(step, dict):
                        continue
                    if str(step.get("conclusion") or "").strip().lower() == "failure":
                        step_name = str(step.get("name") or "").strip()
                        if step_name:
                            return f"{name}: {step_name}" if name else step_name
            if name:
                return name
    path = str(run.get("path") or "").strip()
    if path:
        return path
    return "unknown failing step"


def dedupe_key(
    *,
    github_owner: str,
    github_repo: str,
    workflow_name: str,
    head_branch: str,
    head_sha: str,
) -> str:
    branch = head_branch.strip() or "unknown-branch"
    sha = (head_sha.strip() or "unknown-sha")[:40]
    return (
        f"ci:{github_owner.strip().lower()}/{github_repo.strip().lower()}:"
        f"{workflow_name.strip().lower()}:{branch}:{sha}"
    )
