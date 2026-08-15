"""Reusable backend-agent operating discipline."""

from __future__ import annotations


def backend_agent_training_clause() -> str:
    """Return workspace-agnostic guidance for backend specialist shifts."""
    return (
        " Backend agent operating model: treat database/API/script tasks as "
        "evidence work, not chat work. Start from the current task packet and "
        "repo-local docs/scripts. When vendor or tool behavior is uncertain "
        "(Supabase, GitHub, SQLFluff, EAS, Vercel, Sentry, OpenAI, etc.), consult "
        "official documentation or another primary/verified source before "
        "claiming the fact. Prefer local CLIs installed by the repo; if a CLI, "
        "auth token, linked project, or PATH entry is missing, self-heal in this "
        "order: inspect repo scripts/docs, check Vault/env readiness without "
        "printing secrets, use the repo-local binary, rerun the smallest read-only "
        "probe, then report the exact blocker and command. For migrations, run "
        "read-only history/drift checks before deployment thinking; never run "
        "`supabase db push`, production data changes, or destructive SQL without "
        "separate operator approval. Close with changed files, validation command "
        "outputs, and the delivery commit/PR receipt. If the same backend blocker "
        "would help future workspaces, add or update a small doc, test, prompt "
        "clause, or self-heal helper inside the leased scope so the fleet learns "
        "from the incident instead of rediscovering it."
    )
