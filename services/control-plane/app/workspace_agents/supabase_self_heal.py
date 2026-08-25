"""Prompt guidance for Supabase CLI auth blockers."""

from __future__ import annotations


def dashpro_supabase_self_heal_clause() -> str:
    """Return concise DashPro guidance for Vault-backed Supabase CLI auth."""
    return (
        " Supabase CLI self-heal: if migration/history/diff commands fail because "
        "`SUPABASE_ACCESS_TOKEN` is missing, first check Runtime/Vault readiness "
        "and retry through the normal agent command path so Vault env injection can apply. "
        "If still missing, report secret name `SUPABASE_ACCESS_TOKEN`, project ref, "
        "and the read-only command to rerun; never ask for pasted tokens in chat. "
        "Do not run `supabase db push` without separate operator deployment approval. "
    )
