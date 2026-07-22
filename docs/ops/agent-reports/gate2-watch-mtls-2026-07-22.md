# Watch mTLS / service identity evidence

**Date:** 2026-07-22  
**Closes:** Gate 2 residual “mTLS watch exposure”  
**Handbook:** `docs/how-to/autonomy-gates-and-service-identity.md`

---

## What shipped

1. **Remote token force** — when remotely reachable, watch mutating `/internal/watch/*` requires `AXON_WATCH_INTERNAL_SERVICE_TOKEN` (503 if missing, 401 if wrong).
2. **mTLS gate** — `AXON_WATCH_MTLS_REQUIRED=1` (or CA file present) requires proxy-verified client cert headers (`X-SSL-Client-Verify: SUCCESS`, optional CN allow-list).
3. **CP client certs** — `watch_ssl_context()` / `watch_urlopen()` attach client cert when `AXON_WATCH_MTLS_CLIENT_*` are set.
4. **Mint script** — `./scripts/ops/mint-watch-mtls.sh`
5. **Tests** — `Gate2WatchInternalTokenTests` covers deny without verify header and allow with SUCCESS + CN.

---

## Operator directive (short)

```bash
./scripts/ops/mint-watch-mtls.sh
# add printed env lines to ~/.config/axon-watch/deployment.env
# configure reverse proxy verify headers → watch
axonrestart
```

**Do not** expose `:8788` publicly. **Do** keep token + mTLS together on remote hosts.
