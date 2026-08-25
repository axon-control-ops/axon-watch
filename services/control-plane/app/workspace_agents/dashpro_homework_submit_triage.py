"""DashPro parent homework submit — error ladder for backend/frontend specialists."""

from __future__ import annotations


def dashpro_homework_submit_triage_clause() -> str:
    """Return fleet guidance when homework_submissions parent upload fails."""
    return (
        " DashPro parent homework submit triage (physical worksheet / homework-detail): "
        "read the exact Postgres error string — each layer is a different owner. "
        "(1) `row-level security policy` on homework_submissions → backend/Marco: "
        "parent INSERT+UPDATE policies on published non-practice_at_home assignments; "
        "use get_my_children_ids(); tenant match "
        "COALESCE(students.preschool_id, students.organization_id) for K12 orgs "
        "(Young Eagles); never assert submitted_by=auth.uid() — FK is public.users(id). "
        "(2) `homework_submissions_content_type_check` → Priya maps client payload: "
        "content_type allowed values are text/audio/image/video/pdf/link/mixed/file — "
        "NOT the same set as submission_type (which allows photo/file/drawing). "
        "Legacy JS sent content_type 'file'; migration 20260817213000 adds it. "
        "Prefer lib/homework/resolveHomeworkSubmissionTypes.ts for new code. "
        "(3) `homework_submissions_submission_type_check` → Priya: use file/photo/text, "
        "never 'mixed' on submission_type. "
        "(4) `homework_submissions_submitted_by_fkey` on submitted_by → Priya: call RPC "
        "get_my_homework_submitter_user_id() (lib/homework/resolveHomeworkSubmittedBy.ts); "
        "never send auth.uid() or profiles.id; if RPC returns null use submitted_by null. "
        "Parents cannot SELECT public.users — direct table lookup fails. "
        "Marco adds migration 20260817220000; operator db push required. "
        "Backend writes migrations + `supabase migration list --linked`; "
        "do not run supabase db push or db reset without operator approval. "
        "Integrations/Soren commits and pushes; Frontend/Priya owns hooks/homework/*. "
        "Close with: error layer identified, files changed, migration list receipt, "
        "and whether operator db push is still required."
    )


__all__ = ["dashpro_homework_submit_triage_clause"]
