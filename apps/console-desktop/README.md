# VAXON Desktop (Tauri 2)

Native shell around `apps/console-web` with frozen Watch + Control Plane sidecars.

## Status (honest)

| Piece | Status |
|---|---|
| Packaged `.deb` with SPA + both sidecars | **built** (~59 MB); see `docs/VAXON_DESKTOP_VERIFY_EVIDENCE.md` |
| `npm run verify:desktop` | **PASS** on this host (2026-07-21) |
| Clean VM install without checkout/Python | **not yet recorded** |
| Tray hide-on-close | coded; confirm on your host |
| Host sensors / MPRIS / file index | stub / not implemented |
| Signed CP pairing / keyring | not implemented |

Browser `:4173` remains the preferred day-to-day development path.

## Packaged install

```bash
npm run build:desktop:linux
sudo apt-get install -y ./apps/console-desktop/src-tauri/target/release/bundle/deb/VAXON_*.deb
axon-console-desktop
```

State lives under:

- `~/.config/axon-watch/` (deployment.env, operator token)
- `~/.local/share/axon-watch/state/` (SQLite / runtime state)

Uninstall preserves those directories.

## Dev launcher (repo checkout)

Installed user desktop entry still points at the Vite path for developers:

- Desktop file: `~/.local/share/applications/ai.axon.x.console.desktop`
- Launcher: `scripts/desktop/axon-x-console.sh`
- Requires console-web on `:4173` (or `AXON_X_DEV_URL`)

For `tauri.dev` without frozen sidecars:

```bash
export AXON_DESKTOP_ALLOW_PYTHON_FALLBACK=1
export AXON_WATCH_REPO_ROOT="$PWD"
npm run dev:console-desktop
```

## Dev prerequisites

```bash
sudo apt-get install -y pkg-config libwebkit2gtk-4.1-dev \
  libayatana-appindicator3-dev librsvg2-dev
npm install
source "$HOME/.cargo/env"
```

```bash
# terminal A
npm run dev:console-web

# terminal B
source "$HOME/.cargo/env"
export AXON_DESKTOP_ALLOW_PYTHON_FALLBACK=1
npm run dev:console-desktop
```

## Exposed commands (narrow)

- `get_desktop_bootstrap`
- `host_snapshot` (identity stub)
- `host_evaluate_action`
- `host_post_snapshot`

## Policy

Safe-auto tiers mirror `services/control-plane/app/host_context/policy.py`.
