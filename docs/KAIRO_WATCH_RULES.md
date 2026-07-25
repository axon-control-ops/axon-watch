# KAIRO Watch Rules

## Purpose

Every signal that can influence operator attention carries a canonical
`watch_rule` block:

- `mode`: `observe` | `advise` | `approval` | `execute`
- `reason`: stable machine-readable code
- `interrupts`: whether the signal may interrupt the operator

This slice ports the semantics of `watch_rule_for_item()` from axon-local's
`proactive_next_actions.py` onto canonical inbox items in `axon-watch`.

## Mapping rules

| Condition | Mode | Interrupts |
|---|---|---|
| `source: approval` or `action_type: open_approvals` | `approval` | yes |
| execute action types (`dispatch`, `retry`, `review_changes`) + high/critical severity | `execute` | yes |
| severity `high` or `critical` | `advise` | yes when `critical` |
| severity `warning` | `advise` | no |
| otherwise | `observe` | no |

Explicit `watch_rule` on a signal (e.g. bootstrap summary degraded) is preserved.

## Surfaces

- Watch inbox items include `watch_rule` after ranking + delivery enrichment
- Control-plane `/api/inbox` projects `watch_rule` unchanged
- Attention sidebar shows mode chip (`OBSERVE`, `ADVISE`, etc.) with reason tooltip

## Verification

```bash
npm run verify:test6
# or
./scripts/verify/test6-kairo-watch-rules.sh
```

Unit tests:

- `tests/test_watch_kairo_rules.py`
- `tests/test_control_plane_kairo_rules.py`
- `tests/test_test6_kairo_watch_rules_acceptance.py`

## Cutover status

Locked cutover item **KAIRO watch rules** — verified by TEST-6.

Next locked item: **Spoken alerts, persona, and mobile presence**.
