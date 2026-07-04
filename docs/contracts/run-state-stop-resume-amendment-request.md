# Run-State Stop/Resume Amendment

## Status

**Accepted** — incorporated into the frozen `run-state.md` contract in
`axon-local/Plans/Axon-Watch/`.

## Amendment Summary

The explicit transition list now includes active-phase pause transitions:

- `queued -> paused`
- `starting -> paused`
- `planning -> paused`
- `executing -> paused`

Existing pause/resume transitions remain:

- `waiting_external -> paused`
- `paused -> executing`
- `paused -> cancelled`

## Approval Boundary Clarification

`awaiting_approval` is **not** resumable through the generic resume path.
Forward motion requires explicit `approve` or `reject` actions.

This aligns stop/resume semantics with the approval boundary:

- active phases can pause via stop
- paused runs resume via generic resume
- approval-bound runs advance only through explicit approve/reject

## Implementation Reference

Control-plane implementation lives in:

- `services/control-plane/app/domain/run_transitions.py`
- `services/control-plane/app/runs/service.py`
- `services/control-plane/app/domain/run_state.py`

Verification:

- `tests/test_run_state_transitions.py`
- `tests/test_control_plane_runs.py`
