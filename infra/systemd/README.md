# systemd Units

Supervised startup order for dedicated-server deployment:

1. `axon-watch.service`
2. `control-plane.service` (After=axon-watch)
3. `console-web.service` (After=control-plane)

Install:

```bash
sudo cp infra/systemd/*.service /etc/systemd/system/
sudo cp config/deployment.env.example /etc/axon-watch/deployment.env
# edit /etc/axon-watch/deployment.env for your host
sudo systemctl daemon-reload
sudo systemctl enable --now axon-watch control-plane console-web
```

Services invoke `scripts/ops/run-service.sh` with `EnvironmentFile=/etc/axon-watch/deployment.env`.

See `docs/DEDICATED_SERVER_READINESS.md`.

## User always-on (this machine stays powered)

When the desktop stays on while you are away, install user units instead of
system units:

```bash
./scripts/ops/install-user-always-on.sh
./scripts/ops/install-user-always-on.sh --takeover   # hand ports to systemd
```

Units live under `infra/systemd/user/` (`axon-watch`, `control-plane`,
`console-web`, `axon-public-origin-proxy`) and install to
`~/.config/systemd/user/`. This keeps the stack and Cloudflare's compatibility
origin (`:7734` → Axon-X `:4173`) restarting on failure. Legacy axon-local runs
on the rollback port `:7735`, not the public origin port; the installer disables
its old `:7734` autostart.

Memory caps (user units) stop one runaway service from freezing the desktop:
control-plane MemoryMax=5G, console-web 1G, axon-watch 800M.

One-word health/restart commands (`axonhealth`, `axonrestart`, `axonrevive`) install
via `./scripts/ops/install-bin-wrappers.sh` (included in `install-user-always-on.sh`).

Remote phone access still needs a working Cloudflare tunnel token.
