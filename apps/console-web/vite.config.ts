import { templateCompilerOptions } from '@tresjs/core';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

// Stability is the safe default: source edits must not reload an operator's
// active console. Developers can opt into HMR with AXON_WATCH_VITE_HMR=1.
const hmrEnabled = process.env.AXON_WATCH_VITE_HMR === '1';

function readDeploymentEnvToken(filePath: string): string {
  try {
    if (!fs.existsSync(filePath)) {
      return '';
    }
    for (const rawLine of fs.readFileSync(filePath, 'utf8').split(/\r?\n/)) {
      const line = rawLine.trim();
      if (!line || line.startsWith('#')) {
        continue;
      }
      const match = /^AXON_WATCH_OPERATOR_TOKEN=(.*)$/.exec(line);
      if (!match) {
        continue;
      }
      let value = match[1].trim();
      if (
        (value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))
      ) {
        value = value.slice(1, -1);
      }
      return value.trim();
    }
  } catch {
    // Ignore unreadable deployment env files; proxy stays unauthenticated.
  }
  return '';
}

function resolveOperatorToken(): string {
  const fromEnv = (process.env.AXON_WATCH_OPERATOR_TOKEN || '').trim();
  if (fromEnv && fromEnv !== 'replace-me') {
    return fromEnv;
  }
  const candidates = [
    process.env.AXON_WATCH_DEPLOYMENT_ENV,
    path.join(os.homedir(), '.config', 'axon-watch', 'deployment.env'),
    '/etc/axon-watch/deployment.env',
  ].filter((value): value is string => Boolean(value && value.trim()));
  for (const candidate of candidates) {
    const token = readDeploymentEnvToken(candidate.trim());
    if (token && token !== 'replace-me') {
      process.env.AXON_WATCH_OPERATOR_TOKEN = token;
      return token;
    }
  }
  return '';
}

const proxyOperatorAuthEnabled = ['1', 'true', 'yes', 'on'].includes(
  (process.env.AXON_WATCH_VITE_INJECT_OPERATOR_TOKEN || '').trim().toLowerCase(),
);
const operatorToken = proxyOperatorAuthEnabled ? resolveOperatorToken() : '';

function resolveAllowedHosts(): string[] {
  // Vite preview blocks unknown Host headers. Soft-cutover :7734 rewrote Host to
  // 127.0.0.1; direct Cloudflare ingress to :4173 keeps the public hostname.
  const hosts = new Set<string>(['localhost', '127.0.0.1', '[::1]', '::1']);
  const publicBase = (process.env.AXON_WATCH_PUBLIC_BASE_URL || '').trim();
  if (publicBase) {
    try {
      const hostname = new URL(publicBase).hostname.trim().toLowerCase();
      if (hostname) {
        hosts.add(hostname);
      }
    } catch {
      // Ignore malformed public base URLs; fall back to explicit defaults.
    }
  }
  hosts.add('axon.edudashpro.org.za');
  return [...hosts];
}

const allowedHosts = resolveAllowedHosts();

function injectOperatorAuth(proxyReq: { setHeader: (name: string, value: string) => void }) {
  // Explicit trusted-dev escape hatch only. Default browser traffic must use
  // the HttpOnly operator session; silently injecting the deployment token
  // here bypasses the product login and makes a remote browser indistinguishable
  // from an authenticated operator.
  if (!proxyOperatorAuthEnabled) {
    return;
  }
  const token = operatorToken || (process.env.AXON_WATCH_OPERATOR_TOKEN || '').trim();
  if (!token || token === 'replace-me') {
    return;
  }
  proxyReq.setHeader('Authorization', `Bearer ${token}`);
  proxyReq.setHeader('x-axon-operator-token', token);
}

const controlPlaneProxy = {
  '/api': {
    target: process.env.VITE_CONTROL_PLANE_BASE_URL ?? 'http://127.0.0.1:8787',
    changeOrigin: true,
    ws: true,
    // Lead decompose / agent Full Access can exceed 20s (model plan + materialize).
    // Keep aligned with CHAT_MESSAGE_FETCH_TIMEOUT_MS (60s) so Vite does not
    // kill the socket and the browser reports a bare "Failed to fetch".
    timeout: 90_000,
    proxyTimeout: 90_000,
    configure: (proxy: {
      on: (event: string, listener: (...args: unknown[]) => void) => void;
    }) => {
      proxy.on('proxyReq', (proxyReq: unknown) => {
        injectOperatorAuth(proxyReq as { setHeader: (name: string, value: string) => void });
      });
      // During axonrestart :8787 is briefly down. Answer 503 instead of
      // uncaught ECONNREFUSED spam that looks like a permanent outage.
      proxy.on('error', (err: unknown, _req: unknown, res: unknown) => {
        const code =
          err && typeof err === 'object' && 'code' in err
            ? String((err as { code?: string }).code || '')
            : '';
        const message =
          err instanceof Error ? err.message : typeof err === 'string' ? err : 'proxy error';
        const socket = res as {
          writeHead?: (code: number, headers: Record<string, string>) => void;
          end?: (body?: string) => void;
          headersSent?: boolean;
          writableEnded?: boolean;
        } | undefined;
        if (
          socket &&
          typeof socket.writeHead === 'function' &&
          typeof socket.end === 'function' &&
          !socket.headersSent &&
          !socket.writableEnded
        ) {
          socket.writeHead(503, { 'Content-Type': 'application/json' });
          socket.end(
            JSON.stringify({
              detail: 'control-plane unavailable',
              code: code || 'cp_down',
              hint: 'Waiting for :8787 — axonrestart/axonrevive if it stays down',
            }),
          );
          return;
        }
        if (code === 'ECONNREFUSED' || /ECONNREFUSED/i.test(message)) {
          // eslint-disable-next-line no-console
          console.warn('[vite] control-plane :8787 refused — soft 503 (will recover on restart)');
        }
      });
    },
  },
};

export default defineConfig({
  plugins: [
    vue({
      // TresJS custom renderer tags (TresMesh, TresCanvas children, …)
      ...templateCompilerOptions,
    }),
  ],
  worker: {
    format: 'es',
  },
  server: {
    strictPort: true,
    hmr: hmrEnabled,
    proxy: controlPlaneProxy,
    allowedHosts,
  },
  preview: {
    proxy: controlPlaneProxy,
    allowedHosts,
  },
});
