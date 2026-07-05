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
