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

const operatorToken = resolveOperatorToken();

function injectOperatorAuth(proxyReq: { setHeader: (name: string, value: string) => void }) {
  // Always-on Gate 2: console :4173 → vite /api proxy → CP appears as loopback.
  // With AUTH_ALLOW_LOOPBACK=0 the browser must not rely on loopback bypass;
  // inject the deployment operator token on proxied mutating calls.
  // Dev :5173 also loads ~/.config/axon-watch/deployment.env when the process
  // env is unset (plain `npm run dev` without run-5173.sh).
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
    configure: (proxy: {
      on: (event: string, listener: (...args: unknown[]) => void) => void;
    }) => {
      proxy.on('proxyReq', (proxyReq: unknown) => {
        injectOperatorAuth(proxyReq as { setHeader: (name: string, value: string) => void });
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
  },
  preview: {
    proxy: controlPlaneProxy,
  },
});
