# Working-tree split inventory (Continuous VAXON + Gate 6)

Generated for operator triage. Do **not** treat later-phase files as Phase 1 soak evidence.

## A. Phase 1 reliability (ship first)

- `apps/console-web/src/features/kairo-conversation/kairo-hands-free-loop-policy.ts` (+ test)
- `apps/console-web/src/features/kairo-conversation/use-kairo-hands-free-loop.ts`
- `apps/console-web/src/features/kairo-conversation/use-kairo-conversation.ts` (timeout/cleanup paths)
- `apps/console-web/src/lib/kairo-converse-client.ts` (+ test)
- `apps/console-web/src/lib/kairo-voice-loop-diagnostics.ts` (+ test)
- `scripts/desktop/prove-packaged-voice.sh`
- `docs/VAXON_DESKTOP_VOICE_RELIABILITY_CHECKLIST.md`

## B. Later Continuous VAXON (hold behind Phase 1 soak)

- Wake word / duplex / streaming stubs under `features/kairo-conversation/`
- Presence wake/quiet settings + `spoken_alert_policy.py` quiet hours
- `mission_memory.py` + converse wiring
- `apps/vaxon-android/` + `services/control-plane/app/devices/`
- Orb CSS duplex signatures / `material_change` live events

## C. Unrelated / mixed WIP (do not bundle into VAXON PR)

- HUD holo / cinematic CSS, large mockup-shell CSS churn
- IDE chrome / activity-bar / fleet-health UI edits
- Handbook PDF/HTML churn unless intentionally documented

## D. Gate 6 first slice (parallel track)

- `services/control-plane/app/workspace_agents/verifier_contract.py`
- `services/control-plane/app/runs/service.py` (acceptance enforce + material_change broadcasts)
- `tests/test_gate6_verifier_contract.py`

## Operator action

Prefer two PRs: (1) Phase 1 reliability only, (2) Gate 6 verifier fail-closed.
Keep Android / wake-word / HUD out until soak checklist rows are filled.
