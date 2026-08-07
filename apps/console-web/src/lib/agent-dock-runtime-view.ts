import type { RuntimeStatusSnapshot } from '../api/control-plane';

import { composerRuntimeFamilyLabel } from './cursor-catalog-view';

export type AgentDockRuntimeTone = 'ready' | 'partial' | 'missing' | 'loading' | 'error' | 'vault';

export interface AgentDockRuntimeChip {
  label: string;
  detail: string;
  tone: AgentDockRuntimeTone;
  vaultAction?: boolean;
}

function vaultLockedHint(status: RuntimeStatusSnapshot | null): string | null {
  const posture = status?.vault_runtime?.posture;
  if (posture === 'vault_locked') {
    return status?.vault_runtime?.hint || 'Unlock /vault to inject provider keys into CLI runtimes.';
  }
  const targets = [...(status?.local ?? []), ...(status?.cloud ?? [])];
  if (targets.some((target) => target.ready)) {
    return null;
  }
  if (posture === 'missing_keys') {
    return status?.vault_runtime?.hint || 'Sign in with Cursor, Claude, or Codex CLI on the host or add keys in /vault.';
  }
  return null;
}

export function buildAgentDockRuntimeChip(input: {
  runtimeStatus: RuntimeStatusSnapshot | null;
  loadState: 'idle' | 'loading' | 'loaded' | 'error';
  error?: string | null;
}): AgentDockRuntimeChip {
  if (input.loadState === 'loading' || input.loadState === 'idle') {
    return {
      label: 'Runtime',
      detail: 'Loading runtime fabric…',
      tone: 'loading',
    };
  }
  if (input.loadState === 'error') {
    return {
      label: 'Runtime',
      detail: input.error?.trim() || 'Runtime status unavailable',
      tone: 'error',
    };
  }

  const status = input.runtimeStatus;
  const vaultHint = vaultLockedHint(status);
  if (vaultHint && status?.vault_runtime?.posture === 'vault_locked') {
    return {
      label: 'Vault locked',
      detail: vaultHint,
      tone: 'vault',
      vaultAction: true,
    };
  }

  if (!status) {
    return {
      label: 'Runtime',
      detail: 'No runtime targets configured',
      tone: 'missing',
    };
  }

  const targets = [...status.local, ...status.cloud];
  const selected =
    targets.find((target) => target.id === status.default_runtime) ?? targets[0] ?? null;
  if (!selected) {
    return {
      label: 'Runtime',
      detail: vaultHint || 'No runtime targets configured',
      tone: vaultHint ? 'vault' : 'missing',
      vaultAction: Boolean(vaultHint),
    };
  }

  const label = composerRuntimeFamilyLabel(selected.family);
  const detail = selected.ready
    ? selected.auth.message || 'Runtime ready'
    : selected.auth.message || vaultHint || 'Runtime needs attention';
  const oauthReady =
    selected.ready &&
    (selected.auth.auth_method === 'oauth' || selected.auth.auth_method === 'chatgpt');
  const vaultTone =
    !oauthReady &&
    (selected.auth.vault_posture === 'vault_locked' ||
      selected.auth.vault_posture === 'missing_keys' ||
      selected.auth.auth_method === 'vault_missing_key');

  return {
    label,
    detail,
    tone: selected.ready ? 'ready' : vaultTone ? 'vault' : 'partial',
    vaultAction: vaultTone,
  };
}

function targetNeedsVaultAction(target: RuntimeStatusSnapshot['local'][number]): boolean {
  if (target.ready) {
    return false;
  }
  const method = String(target.auth.auth_method ?? '');
  if (method === 'oauth' || method === 'chatgpt') {
    return false;
  }
  const posture = String(target.auth.vault_posture ?? '');
  return (
    posture === 'vault_locked' ||
    posture === 'missing_keys' ||
    method === 'vault_missing_key' ||
    method === 'vault_locked'
  );
}

export function runtimeNeedsVaultAction(status: RuntimeStatusSnapshot | null): boolean {
  if (!status) {
    return false;
  }
  if (status.vault_runtime?.posture === 'vault_locked') {
    return true;
  }
  const targets = [...status.local, ...status.cloud];
  const preferred =
    targets.find((record) => record.id === status.default_runtime) ?? targets[0] ?? null;
  if (preferred?.ready) {
    return false;
  }
  return targets.some((target) => targetNeedsVaultAction(target));
}

export function runtimeVaultHint(status: RuntimeStatusSnapshot | null): string {
  const postureHint = status?.vault_runtime?.hint?.trim();
  if (postureHint) {
    return postureHint;
  }
  const target =
    status?.local.find((record) => record.id === status.default_runtime) ??
    status?.local[0] ??
    null;
  return target?.auth.message || 'Unlock /vault or sign in to a local CLI runtime.';
}
