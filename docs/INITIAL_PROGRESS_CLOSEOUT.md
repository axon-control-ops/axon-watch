# Initial Progress Closeout

**Closed:** 2026-07-05  
**Primary operator URL:** http://127.0.0.1:4173  
**Fallback URL:** http://127.0.0.1:7734

## Purpose

This document closes the first Axon-X delivery arc as **Initial Progress
COMPLETE**.

That arc includes:

- roadmap Phases 0–11 in `docs/planning/IMPLEMENTATION_ROADMAP.md`
- parity closure Phases A–D in `docs/PARITY_CLOSURE_ROADMAP.md`
- cutover TEST-0 … TEST-10 in `docs/AXON_X_CUTOVER_TODO.md`
- post-cutover Phase E E0–E5 in `docs/TRANSITION_PHASE_E_TODO.md`

It does **not** approve full axon-local retirement.

## What is complete

### Core operator foundation

- production operator shell on `:4173`
- three-service local stack (`:4173`, `:8787`, `:8788`)
- operator / IDE shell split
- Monaco workspace editing
- PTY terminal attachment
- Mission Control, Attention, and KAIRO briefing surfaces
- bounded command executor (`read`, `list`, `git status`, `resume from review`)

### Verified governance and parity

- parity closure A–D complete (`19/19` verified v1)
- cutover TEST-0 … TEST-10 complete
- Phase E E0–E5 complete
- child-project workspace binding for DashPro (`workspace_dashpro`)

### Primary source docs

- `docs/PRODUCTION_OPERATOR_SURFACE.md`
- `docs/CHILD_PROJECT_WORKSPACE.md`
- `docs/PARITY_CLOSURE_ROADMAP.md`
- `docs/AXON_X_CUTOVER_TODO.md`
- `docs/TRANSITION_PHASE_E_TODO.md`

## What exists only as scaffold

The following work is checkpointed in code, but is **not** the approved end-state:

| Area | Current state | Closeout decision |
|---|---|---|
| IDE Lane B | Separate IDE conversation path + local-model bridge checkpoint | Keep only as an interim scaffold; replace with runtime fabric in Phase F1 |
| DashPro monitors | Sentry/PostHog monitor modules and inbox projection | Keep and finish in Phase F4 after vault/runtime work |
| Vault backend | Import resolver + status helpers | Keep and surface through `/vault` in Phase F2 |
| IDE polish | Distinct IDE chrome + Mission Control scroll fix | Keep and finish in Phase F5 |

## What remains outside Initial Progress

Initial Progress deliberately stops short of:

- runtime fabric with Cursor/Codex local + cloud workers
- dedicated vault surface
- dedicated data / DB surface
- finished DashPro monitor signals in operator UX
- final operator/IDE polish closure
- full axon-local retirement approval

## Architecture corrections locked for the next phase

The next phase is based on official runtime and agent guidance:

- [Cursor CLI](https://cursor.com/docs/cli/overview)
- [Cursor Hooks](https://cursor.com/docs/hooks)
- [OpenAI Codex CLI](https://developers.openai.com/codex/cli)
- [Codex non-interactive mode](https://developers.openai.com/codex/noninteractive)
- [OpenAI Agents SDK](https://developers.openai.com/api/docs/guides/agents.md)
- [OpenAI agent evals](https://developers.openai.com/api/docs/guides/agent-evals)
- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents?lang=en-US)
- [Anthropic: Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [MCP specification](https://modelcontextprotocol.io/specification/2025-11-25/index)

These sources imply four explicit corrections:

1. Axon-X owns orchestration, approvals, state, and receipts.
2. Cursor and Codex are replaceable runtimes, not the source of truth.
3. MCP is the standard native-tools integration fabric.
4. Continuous improvement comes from traces, evals, and operator review, not
   hidden self-modification.

## Next source of truth

All follow-on build work moves to:

- `docs/PHASE_F_OPERATOR_FOUNDATION.md`

Phase E remains historical closeout. E6 stays deferred until Phase F is green.
