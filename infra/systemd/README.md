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

Units live under `infra/systemd/user/` and install to `~/.config/systemd/user/`.
This keeps **watch + control-plane + console-web (:4173)** restarting on failure.
Legacy axon-local **:7734** is not started — run
`./scripts/ops/disable-legacy-7734-autostart.sh` (also invoked by the installer).

Memory caps (user units) stop one runaway service from freezing the desktop:
control-plane MemoryMax=5G, console-web 1G, axon-watch 800M.

Remote phone access still needs a working Cloudflare tunnel token.
