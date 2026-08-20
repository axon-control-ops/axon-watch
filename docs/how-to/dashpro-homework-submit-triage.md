# DashPro — parent homework submit failures (fleet playbook)

When a parent sees **Submit to Teacher** fail on `homework-detail` / physical worksheet upload, read the **exact** error string. Each message is a different layer and a different owner.

## Error ladder

| Error contains | Layer | Owner | Fix |
|----------------|-------|-------|-----|
| `row-level security policy` + `homework_submissions` | RLS | **Marco** (backend) | Parent INSERT/UPDATE policies; `get_my_children_ids()`; K12 tenant via `COALESCE(preschool_id, organization_id)`; migrations `20260817194500`, `20260817201500` |
| `homework_submissions_content_type_check` | CHECK constraint | **Priya** (frontend) + **Marco** if enum gap | Map payload to allowed `content_type`: `text`, `audio`, `image`, `video`, `pdf`, `link`, `mixed`, `file`. Legacy JS sent `'file'` before DB allowed it — migration `20260817213000`. Use `lib/homework/resolveHomeworkSubmissionTypes.ts` |
| `homework_submissions_submission_type_check` | CHECK constraint | **Priya** | Allowed: `text`, `photo`, `video`, `audio`, `file`, `drawing` — **not** `mixed` |
| `homework_submissions_submitted_by_fkey` / FK / `submitted_by` | Client RPC + schema | **Priya** + **Marco** | FK → `public.users(id)`. **Never** send `auth.uid()` or `profiles.id`. Use RPC `get_my_homework_submitter_user_id()` (`lib/homework/resolveHomeworkSubmittedBy.ts`, migration `20260817220000`). If unresolved, send `submitted_by: null` — not a wrong UUID. Parent clients **cannot** `SELECT public.users`. |
| `Network request failed` (Android gallery) | Client read path | **Priya** | `readUploadBodyFromUri` — not a DB issue |

**Not the same column:** `content_type` and `submission_type` have **different** allowed value lists. Do not copy one to the other.

## Role split

- **Dana (Lead):** Fan-out P0 with evidence (assignment id, student id, parent email, screenshot). Do not keep backend work on the Lead thread.
- **Marco (Backend):** SQL migrations, `supabase migration list --linked`, static policy review. **Never** `supabase db push` or `db reset` without operator approval.
- **Priya (Frontend):** `hooks/homework/useHomeworkDetail.ts`, payload mapping, OTA/canary receipt.
- **Soren (Integrations):** Commit, push `development`, watch CI — does **not** design RLS.

## Marco verification checklist

```bash
cd /run/media/vaxon/axon-data/projectx/product/dashpro
node_modules/.bin/supabase migration list --linked
```

Confirm applied (local = remote): `20260817194500`, `20260817201500`, `20260817213000`, `20260817220000`.

**Note:** These were applied to the linked Supabase project by the operator via `supabase db push` during incident response — not by Marco in sandbox. Agents write migration files; operator (or approved Integrations step) pushes.

Inspect policies (read-only): parent submit insert/update exist on `homework_submissions`.

## Control plane prompt injection

The triage clause is appended to **continuous worker prompts** for `workspace_dashpro` only (`worker_prompt.py`). Restart or redeploy the control plane after changing prompt modules, or Marco will not see updated guidance until the process reloads.

## Applying Sandbox changes to the root worktree

Composer Sandbox edits live in a **disposable git worktree** (or isolation checkout), not the bound project root. Two paths:

### A. UI (recommended)

1. Open **DashPro** in Axon-X → Agent Dock → ensure **Sandbox** is on.
2. **Review** — inspect changed files/diffs in the sandbox checkout.
3. **Preview** (optional) — dev server against sandbox checkout only.
4. Ensure **root worktree is clean** (no uncommitted changes on `bound_project_root`). If dirty, commit/stash root first — publish is blocked otherwise (`DirtySandboxError`).
5. Click **Publish** — calls `POST /api/workspaces/{id}/sandbox/publish`, runs `publish_worker_isolation` (commit on worker branch → draft PR per delivery policy). This is **not** a silent overwrite of root; it goes through the normal delivery gate.
6. Merge the draft PR (or complete delivery flow) to land changes on the bound branch.

### B. Manual (when sandbox is DashPro repo path)

If changes exist only in the sandbox checkout path (shown in sandbox status as `checkout_root`):

```bash
# From bound root — example paths; use checkout_root from sandbox status API
BOUND=/run/media/vaxon/axon-data/projectx/product/dashpro
SANDBOX=<checkout_root from GET /api/workspaces/workspace_dashpro/sandbox>

# Inspect diff first
git -C "$SANDBOX" diff --stat

# Copy specific files (example — prefer Publish UI for full delivery)
cp "$SANDBOX/hooks/homework/useHomeworkDetail.ts" "$BOUND/hooks/homework/"
```

Manual copy bypasses the delivery gate — use for emergency operator fixes only; prefer **Publish** for fleet work.

### What Sandbox does *not* do

- Does **not** auto-apply DB migrations to Supabase (filesystem only).
- Does **not** replace `supabase db push` — operator still deploys SQL separately.
- Discarding sandbox **deletes** unpromoted work (Marco’s lost untracked migration).

## Operator deploy

Only the operator (or explicit approval) runs:

```bash
node_modules/.bin/supabase db push
```

Agents in sandbox write migration **files** and report pending version; they do not push to production Postgres from the disposable worktree.

## Dispatch prompt (Composer Agent mode, DashPro)

```
P0: Parent homework submit failing on homework-detail.
Error: <paste exact string>.
Assignment: <uuid>. Student: <uuid>.
Have Marco identify the layer (RLS vs CHECK vs FK), confirm migration list, write migration if needed.
Have Priya fix client payload if CHECK/FK.
Have Soren commit and push when approved. No db reset.
```

## References

- `services/control-plane/app/workspace_agents/dashpro_homework_submit_triage.py` — injected into DashPro worker prompts
- `lib/homework/resolveHomeworkSubmissionTypes.ts` — canonical client mapping
- `docs/how-to/supabase-cli-auth.md` — Vault / `migration list` auth
