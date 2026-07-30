# Native tunnel control

Axon-X owns Cloudflare tunnel start, stop, and status directly. It does not call
`axon-local/tunnel.sh` or require `AXON_LOCAL_ROOT`.

## Runtime contract

- Configuration: `config/tunnel-slice.json`
- Control service: `services/axon-watch/app/tunnel/tunnel_control.py`
- Process ownership: `services/axon-watch/app/tunnel/native_process.py`
- API: `/api/tunnel/status`, `/api/tunnel/start`, `/api/tunnel/stop`
- Operator surface: Mission Control → Connectors

The configured `cloudflared` binary is resolved from the Axon-X state directory
or `PATH`. Named-tunnel credentials are resolved from settings, environment,
the Axon-X vault import, or documented legacy credential files. Tokens are
passed through the child environment and are never included in process
arguments or process-state files.

The local tunnel origin is the Axon-X operator at `http://127.0.0.1:4173`; it
does not route through the legacy `:7734` service.

The current Cloudflare remote ingress still targets `http://localhost:7734`.
Axon-X owns that compatibility hop through
`axon-public-origin-proxy.service`, which forwards `:7734` to `:4173`, listens
on IPv4 and IPv6 localhost, and restarts automatically after a process crash.
`scripts/ops/soft-public-cutover.sh` uses the service when installed and only
falls back to a detached process for development checkouts.

Axon-X writes a process ownership record and log under
`AXON_WATCH_STATE_DIR/tunnel/`. Start is idempotent. Stop only signals the exact
process recorded and validated as Axon-X-managed; it refuses to kill an
unmanaged Cloudflare process.

## Startup autostart

On watch service startup (after vault auto-unlock), `attempt_tunnel_autostart`
best-effort starts the configured tunnel when the slice is enabled. Failures are
logged and never block service readiness — missing `cloudflared`, auth, or an
already-running unmanaged process should not prevent the watch stack from booting.

- Default: enabled (`AXON_WATCH_TUNNEL_AUTOSTART=1`)
- Disable locally: set `AXON_WATCH_TUNNEL_AUTOSTART` to `0`, `false`, `no`, or `off`

## Migration note

If an old tunnel is still owned by `axon-local`, stop that legacy process once
before using Axon-X Start. Axon-X reports an unmanaged running process instead
of taking destructive ownership.

## Verification

```bash
npm run verify:tunnel-remote-control
```

The gate proves binary/auth diagnostics, native command construction, token
redaction from arguments, control delegation, unmanaged-process protection,
startup autostart (disable / slice-off / success / error swallowing),
the control-plane proxy, and connector-inventory consistency.

WhatsApp monitoring is a separate retirement item and remains explicitly
deferred.
