# VAXON Desktop (Tauri 2) — scaffold

Packages `apps/console-web` inside a native shell with a **narrow** Rust bridge.

## Current status (honest)

| Piece | Status |
|---|---|
| Project layout (`src-tauri`) | present |
| Tray hide-on-close | coded, not verified on this host |
| Host policy mirror | unit-tested in Python; Rust needs GTK deps to compile |
| Real sensors / file index / MPRIS | **not implemented** (snapshot is identity stub) |
| Signed CP pairing / keyring | **not implemented** |
| Compact HUD / autostart / deep links | **not implemented** |

Browser `:4173` remains the supported operator path.

## Desktop launcher (Linux)

Installed for the current user as **Axon-X Operator Console** (not the older
“Axon Desktop” axon-local entry):

- Desktop file: `~/.local/share/applications/ai.axon.x.console.desktop`
- Icon: `ai.axon.x.console`
- Repo copy: `apps/console-desktop/packaging/ai.axon.x.console.desktop`
- Launcher: `scripts/desktop/axon-x-console.sh`

Requires console-web on `:4173` (or `AXON_X_DEV_URL`).

## Dev prerequisites

```bash
sudo apt-get install -y pkg-config libwebkit2gtk-4.1-dev \
  libayatana-appindicator3-dev librsvg2-dev
npm install
source "$HOME/.cargo/env"
```

`tauri.dev` reuses the existing console-web Vite on `:4173` (does not start a
second Vite). Keep browser/preview up first:

```bash
# terminal A — already your normal path
npm run dev:console-web
# or whatever already serves http://127.0.0.1:4173

# terminal B — desktop shell
source "$HOME/.cargo/env"
npm run dev:console-desktop
```

Control-plane should be on `:8787` for host-bridge POSTs.

## Exposed commands (narrow)

- `get_desktop_bootstrap`
- `host_snapshot` (identity stub)
- `host_evaluate_action`
- `host_post_snapshot`

## Policy

Safe-auto tiers mirror `services/control-plane/app/host_context/policy.py`.
