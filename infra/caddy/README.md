# Caddy Reverse Proxy

`Caddyfile.example` routes:

- `/api/*` → control-plane (8787)
- `/` → built console-web static assets

Watch internal routes (`/internal/watch/*`) are **not** exposed publicly.

See `docs/DEDICATED_SERVER_READINESS.md`.
