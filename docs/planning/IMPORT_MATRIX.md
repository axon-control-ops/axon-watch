# Axon-Watch Import Matrix

## Purpose

This document governs what may be reused from the current
`/home/edp/axon-nvme/repos/axon-local` repo when building the new
`/home/edp/axon-nvme/repos/axon-watch` product.

Every imported capability must be classified before implementation.

## Status Meanings

- `adopt`
  Reuse concept or shape mostly as-is, with minimal change.
- `adapt`
  Reuse the concept, but reimplement it cleanly for the new architecture.
- `rewrite`
  Keep the product need, but rebuild from scratch.
- `discard`
  Do not carry this forward.

## Import Rules

1. Import behavior, not baggage.
2. Prefer contract and UX reuse over file-level code reuse.
3. Do not copy monoliths into the new repo.
4. Every adopted or adapted item must name its new owner.
5. If an item fights the new stack or boundary model, rewrite or discard it.

## Product Concepts

| Current capability | Status | New owner | Notes |
|---|---|---|---|
| Operator control-plane thesis | `adopt` | `PRODUCT.md`, `control-plane` | Core identity should carry forward |
| Multi-workspace oversight | `adopt` | `control-plane`, `console-web` | Important differentiator |
| Attention / inbox concept | `adapt` | `axon-watch`, `control-plane` | Keep the concept, normalize schema |
| Workspace handoffs | `adapt` | `control-plane` | Keep behavior, reimplement cleanly |
| Mission terminology if still useful | `adapt` | product docs | Keep only if it fits the new product vocabulary |

## Frontend / UX Patterns

| Current capability | Status | New owner | Notes |
|---|---|---|---|
| Operator mode vs IDE mode concept | `adopt` | `console-web` | Strong concept, keep |
| Agent dock behavior | `adapt` | `console-web/rightDock` | Rebuild in Vue |
| Workbench status hierarchy | `adapt` | run-presentation layer | Keep one-owner status philosophy |
| Workspace tab concept | `adapt` | `console-web` | Rebuild with new state model |
| Signal/inbox surfaces | `adapt` | `console-web`, `control-plane` | Keep concept, new DTOs |
| Alpine boot flow | `discard` | n/a | Not appropriate for new stack |
| Large HTML shell patterns | `discard` | n/a | Replace with componentized UI |
| Inline UI logic inside shell files | `discard` | n/a | No carry-over |

## Backend Architecture

| Current capability | Status | New owner | Notes |
|---|---|---|---|
| Proactive watcher concept | `adapt` | `axon-watch` | Keep concept, move to dedicated service |
| Signal correlation | `adapt` | `axon-watch` | Rebuild behind canonical event model |
| Operator recommendations | `adapt` | `control-plane` | Keep capability, tie to new contracts |
| Runtime truth discipline | `adopt` | `control-plane` | Strong principle to preserve |
| In-process scheduler monolith | `discard` | n/a | Replace with watch workers + explicit orchestration |
| Giant route modules | `discard` | n/a | Replace with bounded APIs |
| Hotspot-heavy mixed ownership files | `discard` | n/a | Do not inherit |

## Execution Model

| Current capability | Status | New owner | Notes |
|---|---|---|---|
| ReAct-style reasoning within a step | `adapt` | run execution nodes | Keep as a technique, not as system truth |
| Exact approval boundaries | `adopt` | `control-plane` | Must remain a product strength |
| Plan mode concept | `adapt` | run-state + UI | Keep concept, tie to explicit phases |
| Implicit state from prompt text | `discard` | n/a | Replace with persisted run-state |

## Runtime / AI Orchestration

| Current capability | Status | New owner | Notes |
|---|---|---|---|
| Cursor CLI agent loop | `adapt` | `services/control-plane/app/cli_runtime/cursor_agent.py` | Primary live workspace runtime for Ask/Plan/Agent |
| Codex CLI agent loop | `adapt` | `services/control-plane/app/cli_runtime/codex_agent.py` | Primary automation/runtime worker for scripted and batch flows |
| CLI binary catalog / resolve | `adapt` | `services/control-plane/app/cli_runtime/catalog.py` | Keep explicit runtime discovery and health |
| Cursor -> Codex reroute / recovery | `adapt` | `services/control-plane/app/cli_runtime/recovery.py` | Preserve fallback idea, rebuild cleanly |
| Cursor cloud agents / automations | `adapt` | `services/control-plane/app/cli_runtime/cloud_cursor.py` | Cloud path belongs in Axon-X runtime fabric, not hidden in prompts |
| Codex cloud tasks | `adapt` | `services/control-plane/app/cli_runtime/cloud_codex.py` | Durable automation / best-of-N / background tasks |
| Model Context Protocol (MCP) integration | `adopt` | control-plane tool fabric + watch integrations | MCP is the standard native-tools contract |
| Local model bridge / Ollama path | `discard` | n/a | Not the approved operator architecture target for Phase F |

## Delivery / Notifications

| Current capability | Status | New owner | Notes |
|---|---|---|---|
| Notification policy concept | `adapt` | `axon-watch` | Keep policy layer, normalize receipts |
| Push / desktop / webhook delivery idea | `adapt` | `axon-watch` | Keep channels, clean contracts |
| Ad hoc alert logic in multiple places | `discard` | n/a | Consolidate |

## KAIRO / Operator Presence

| Current capability | Status | New owner | Notes |
|---|---|---|---|
| JARVIS operator loop (`watch -> notice -> advise -> approve -> execute -> verify`) | `adopt` | product docs + service boundaries | Adopt as `KAIRO` in AXON-X; maps directly to the new architecture |
| `watch_rule_for_item()` semantics | `adapt` | `axon-watch` signal ranking/policy | Preserve observe/advise/approval/execute modes |
| `jarvis_personality.py` | `adapt` | `packages/prompt-contracts` | Persona is presentation, not orchestration truth |
| `toggleJarvisMode()` preset behavior | `adapt` | `console-web` operator-presence settings | Split into explicit presence settings |
| VCD / voice deck orchestration | `adapt` | `console-web/features/operator-presence` | Rebuild in Vue against canonical DTOs |
| Voice attention polling in Alpine modules | `rewrite` | `console-web` store + watch/control events | Replace polling with event-driven presence |
| Executive operator workflow | `adapt` | `control-plane` briefing/orchestration | Keep rhythm, reimplement against run-state |
| Mobile JARVIS controller behavior | `adapt` | `console-web` mobile operator cockpit | Keep compact field-unit UX |
| Background mobile listening claims | `discard` until proven | docs only | Foreground + push remains honest v1 model |
| Scattered `speakMessage()` as interruption policy | `discard` | n/a | Replace with policy-driven spoken alerts |

## Data / Persistence

| Current capability | Status | New owner | Notes |
|---|---|---|---|
| SQLite local-first posture | `adopt` | both services via adapters | Good phase-1 choice |
| Split ownership by concern | `adapt` | persistence layer | Preserve principle, refine implementation |
| Hidden direct DB reach-through | `discard` | n/a | Replace with explicit ownership and contracts |
| Secure vault (full crypto parity) | `adapt` | `services/axon-watch/app/vault/*` + dedicated `/vault` UI | **F2 done:** import/status/consumer UX. **G1 (Vault II):** full crypto/session/CRUD/export parity — see `docs/PHASE_G_SIGNAL_PARITY.md` |
| DashPro external monitors | `adapt` | `services/axon-watch/app/monitors/*` | Keep the behavior, route it through watch signals |

## Developer Experience

| Current capability | Status | New owner | Notes |
|---|---|---|---|
| Guardrail mindset | `adopt` | new repo rules/docs | Strong principle worth preserving |
| Thin-slice delivery discipline | `adopt` | roadmap + repo rules | Keep |
| Repo-wide planning sprawl | `discard` | n/a | New repo should stay cleaner |

## Decision Rule

When uncertain:

- if the current artifact is a principle or UX insight, prefer `adopt` or `adapt`
- if it is a tangled implementation, prefer `rewrite` or `discard`

## Acceptance Criteria

This matrix is being followed when:

- copied behavior has a documented new owner
- no large legacy file is imported by convenience
- the new repo preserves strengths while reducing inherited complexity
