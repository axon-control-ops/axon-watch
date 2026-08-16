import { fetchJson } from './client';

/**
 * Real per-workspace disposable isolation for the Agent Dock composer's
 * Sandbox toggle — distinct from `/api/safe-improvement/session`, which
 * gates the separate safe-improvement proposal pipeline and never affected
 * where composer messages actually dispatched.
 */
export type ComposerSandboxStatus = {
  enabled: boolean;
  session_enabled: boolean;
  env_forced: boolean;
  source: 'off' | 'session' | 'env' | string;
  manual_enabled: boolean;
  auto_enabled: boolean;
  materialized: boolean;
  dirty: boolean;
  effective_access: 'full' | 'operator' | string;
  retained_reason: string;
  can_disable: boolean;
  checkout_id: string | null;
  lifecycle: 'off' | 'auto-ready' | 'active' | 'retained-dirty' | string;
};

export async function fetchComposerSandboxStatus(
  workspaceId: string,
): Promise<ComposerSandboxStatus> {
  const encoded = encodeURIComponent(workspaceId);
  return fetchJson<ComposerSandboxStatus>(
    `/api/workspaces/${encoded}/sandbox`,
    {},
    'sandbox session status request failed',
  );
}

export async function reviewComposerSandbox(workspaceId: string): Promise<ComposerSandboxStatus & { changed_paths: string[] }> {
  return fetchJson(`/api/workspaces/${encodeURIComponent(workspaceId)}/sandbox/review`, {}, 'review sandbox session failed');
}

export async function publishComposerSandbox(workspaceId: string): Promise<ComposerSandboxStatus> {
  return fetchJson(`/api/workspaces/${encodeURIComponent(workspaceId)}/sandbox/publish`, { method: 'POST' }, 'publish sandbox session failed');
}

export async function discardComposerSandbox(workspaceId: string): Promise<ComposerSandboxStatus> {
  return fetchJson(`/api/workspaces/${encodeURIComponent(workspaceId)}/sandbox/discard`, { method: 'POST' }, 'discard sandbox session failed');
}

export async function enableComposerSandbox(
  workspaceId: string,
): Promise<ComposerSandboxStatus> {
  const encoded = encodeURIComponent(workspaceId);
  return fetchJson<ComposerSandboxStatus>(
    `/api/workspaces/${encoded}/sandbox/enable`,
    { method: 'POST' },
    'enable sandbox session failed',
  );
}

export async function disableComposerSandbox(
  workspaceId: string,
): Promise<ComposerSandboxStatus> {
  const encoded = encodeURIComponent(workspaceId);
  return fetchJson<ComposerSandboxStatus>(
    `/api/workspaces/${encoded}/sandbox/disable`,
    { method: 'POST' },
    'disable sandbox session failed',
  );
}
