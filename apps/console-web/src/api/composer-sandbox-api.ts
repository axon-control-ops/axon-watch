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
  checkout_root: string;
  checkout_id: string | null;
  bound_project_root: string;
  bound_branch: string;
  root_dirty: boolean;
  root_changed_paths: string[];
  lifecycle: 'off' | 'auto-ready' | 'active' | 'retained-dirty' | string;
};

/** One changed file in the sandbox checkout, with its unified diff. */
export type SandboxFileDiff = {
  path: string;
  diff: string;
  added: number;
  removed: number;
};

export type ComposerSandboxReview = ComposerSandboxStatus & {
  changed_paths: string[];
  file_diffs?: SandboxFileDiff[];
  baseline: Record<string, unknown>;
  preview: {
    available: boolean;
    detail: string;
    checkout_root?: string;
    bound_project_root?: string;
    running?: boolean;
    url?: string;
    port?: number | null;
    job_id?: string;
    sandbox_url_hint: string;
    root_url_hint?: string;
    example?: string;
    workspace_id?: string;
  };
};

/** A dev server running against the Sandbox checkout, not the bound root. */
export type ComposerSandboxPreview = {
  workspace_id: string;
  running: boolean;
  reused?: boolean;
  stopped?: boolean;
  job_id?: string;
  port?: number;
  url?: string;
  command?: string;
  checkout_root?: string;
  timeout_seconds?: number;
  /** How the checkout got its node_modules (worktrees have none of their own). */
  dependencies?: string;
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

export async function reviewComposerSandbox(workspaceId: string): Promise<ComposerSandboxReview> {
  return fetchJson(`/api/workspaces/${encodeURIComponent(workspaceId)}/sandbox/review`, {}, 'review sandbox session failed');
}

export async function fetchComposerSandboxPreview(
  workspaceId: string,
): Promise<ComposerSandboxPreview> {
  return fetchJson(
    `/api/workspaces/${encodeURIComponent(workspaceId)}/sandbox/preview`,
    {},
    'sandbox preview status request failed',
  );
}

export async function startComposerSandboxPreview(
  workspaceId: string,
): Promise<ComposerSandboxPreview> {
  return fetchJson(
    `/api/workspaces/${encodeURIComponent(workspaceId)}/sandbox/preview`,
    { method: 'POST' },
    'start sandbox preview failed',
  );
}

export async function stopComposerSandboxPreview(
  workspaceId: string,
): Promise<ComposerSandboxPreview> {
  return fetchJson(
    `/api/workspaces/${encodeURIComponent(workspaceId)}/sandbox/preview`,
    { method: 'DELETE' },
    'stop sandbox preview failed',
  );
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

/** A dev server holding a port in the sandbox preview range. */
export type SandboxPreviewProcess = {
  port: number;
  url: string;
  pid: number;
  process: string;
  /** False for orphans — e.g. a server that outlived a control-plane restart. */
  managed: boolean;
  job_id?: string;
  command?: string;
  checkout_root?: string;
};

export async function listSandboxPreviews(
  workspaceId: string,
): Promise<{ workspace_id: string; items: SandboxPreviewProcess[]; count: number }> {
  return fetchJson(
    `/api/workspaces/${encodeURIComponent(workspaceId)}/sandbox/previews`,
    {},
    'sandbox preview list request failed',
  );
}

export async function stopSandboxPreviewPort(
  workspaceId: string,
  port: number,
): Promise<{ port: number; stopped: boolean; detail?: string }> {
  return fetchJson(
    `/api/workspaces/${encodeURIComponent(workspaceId)}/sandbox/previews/${port}`,
    { method: 'DELETE' },
    'stop sandbox preview failed',
  );
}
