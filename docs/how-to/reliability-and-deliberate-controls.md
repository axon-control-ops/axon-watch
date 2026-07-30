# Reliability and deliberate controls

**Updated:** 2026-07-29

This chapter records the operator-facing reliability contract for the local
console, Command Theater, voice playback, and IDE AgentDock.

## Control-plane restart contract

- `control-plane.service` uses `Restart=always` and a short stop timeout.
- Its relationship with `axon-watch.service` is soft: a watch-service flap must
  not stop the control-plane.
- `axonrestart` restarts the control-plane first and waits for `:8787` health
  before continuing through the remaining units.
- Use `axonrevive` when the process is wedged rather than merely restarting.

## Vite control-plane recovery

Start the source console through the guarded wrapper:

```bash
./scripts/ops/run-5173.sh
```

The wrapper checks `http://127.0.0.1:8787/api/health`, starts
`control-plane.service` when necessary, and waits before starting Vite. If the
API restarts while Vite remains up, `/api/*` returns a temporary JSON `503`
instead of exposing `ECONNREFUSED`, then recovers to `200`.

```bash
./scripts/verify/verify-vite-cp-restart.sh
```

If recovery fails:

```bash
systemctl --user status control-plane.service
journalctl --user -u control-plane.service -n 80
axonrevive
```

## Deliberate STAND-UP

Command Theater must open only from the STAND-UP control or an explicit VAXON
request. Briefing polls do not auto-start it. The browser smoke check asserts
that the theater is closed before the operator clicks.

## Speech onset and stage synchronization

Azure output includes backend lead silence, while the browser player waits for
audio readiness and preroll. The report stage changes from the audible-start
callback, not from fetch completion, so the visible speaker and first audible
word stay aligned. Browser speech uses its own short start guard.

## AgentDock operator-message actions

In IDE AgentDock, **Edit** and **Resend** reserve their layout space but remain
visually hidden until:

- the operator message is hovered with a fine pointer, or
- keyboard focus enters either action.

Touch and coarse-pointer devices keep the controls visible because they have no
reliable hover state. Reduced-motion users get the same visibility behavior
without the transition.

Verify the structural and interaction contract:

```bash
./scripts/dev/python.sh scripts/verify/check_dock_behavior_contract.py
npm run typecheck -w @axon-watch/console-web
```
