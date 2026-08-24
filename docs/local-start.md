# Local Start

Run these commands from the repo root.

## Full local stack

```bash
npm install
npm run dev
```

That starts:

- console web at `http://127.0.0.1:4173`
- control plane at `http://127.0.0.1:8787`
- watch service at `http://127.0.0.1:8788`

Useful follow-ups:

```bash
npm run health
npm run down
```

## Web version only

```bash
npm install
npm run dev:console-web
```

That starts the web console at:

- `http://127.0.0.1:4173`

Important note:

- `dev:console-web` proxies `/api` to `http://127.0.0.1:8787`
- if the control plane is not already running, the web shell will load but API-backed features will not work

## Optional single-service starts

```bash
npm run dev:control-plane
npm run dev:axon-watch
npm run dev:console-mobile
```
