import { fetchJson } from './client';

export type SandboxSessionStatus = {
  enabled: boolean;
  session_enabled: boolean;
  env_forced: boolean;
  source: 'off' | 'session' | 'env' | string;
};

export async function fetchSandboxSessionStatus(): Promise<SandboxSessionStatus> {
  return fetchJson<SandboxSessionStatus>(
    '/api/safe-improvement/session',
    {},
    'sandbox session status request failed',
  );
}

export async function enableSandboxSession(): Promise<SandboxSessionStatus> {
  return fetchJson<SandboxSessionStatus>(
    '/api/safe-improvement/session/enable',
    { method: 'POST' },
    'enable sandbox session failed',
  );
}

export async function disableSandboxSession(): Promise<SandboxSessionStatus> {
  return fetchJson<SandboxSessionStatus>(
    '/api/safe-improvement/session/disable',
    { method: 'POST' },
    'disable sandbox session failed',
  );
}
