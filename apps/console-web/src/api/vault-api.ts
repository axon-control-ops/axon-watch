import type {
  VaultSecretDetail,
  VaultSecretRecord,
  VaultSentryValidation,
  VaultStatusSnapshot,
} from '../lib/vault-surface-view';

import { apiUrl, DEFAULT_FETCH_TIMEOUT_MS, fetchBlob } from './client';

export interface VaultImportResult {
  imported_keys: string[];
  count: number;
}

export interface VaultStatusResponse {
  vault: VaultStatusSnapshot;
}

export interface VaultImportResponse extends VaultStatusResponse {
  vault_import: VaultImportResult;
}

export interface VaultSetupResponse {
  totp_secret: string;
  qr_data_uri: string;
}

export interface VaultUnlockResponse {
  unlocked: boolean;
  session_ttl: number;
  ttl_label: string;
  migrated_settings: string[];
}

async function vaultRequest<T>(
  path: string,
  init: RequestInit = {},
  timeoutMs: number = DEFAULT_FETCH_TIMEOUT_MS,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => {
    controller.abort(new DOMException(`request timed out after ${timeoutMs}ms`, 'TimeoutError'));
  }, timeoutMs);
  const onExternalAbort = () => {
    controller.abort(init.signal?.reason);
  };
  if (init.signal) {
    if (init.signal.aborted) {
      onExternalAbort();
    } else {
      init.signal.addEventListener('abort', onExternalAbort, { once: true });
    }
  }
  try {
    const response = await fetch(apiUrl(path), { ...init, signal: controller.signal });
    if (!response.ok) {
      let detail = `request failed with status ${response.status}`;
      try {
        const payload = (await response.json()) as { detail?: string };
        if (payload.detail) {
          detail = payload.detail;
        }
      } catch {
        // ignore parse errors
      }
      throw new Error(detail);
    }
    if (response.status === 204) {
      return {} as T;
    }
    const contentType = response.headers.get('content-type') ?? '';
    if (!contentType.includes('application/json')) {
      return (await response.blob()) as T;
    }
    return response.json() as Promise<T>;
  } catch (error) {
    if (error instanceof DOMException && error.name === 'TimeoutError') {
      throw new Error(`request timed out after ${timeoutMs}ms`);
    }
    if (error instanceof Error && error.name === 'AbortError') {
      if (init.signal?.aborted) {
        throw error;
      }
      throw new Error(`request timed out after ${timeoutMs}ms`);
    }
    throw error;
  } finally {
    clearTimeout(timer);
    init.signal?.removeEventListener('abort', onExternalAbort);
  }
}

export async function fetchVaultStatus(): Promise<VaultStatusResponse> {
  return vaultRequest<VaultStatusResponse>('/api/vault/status');
}

export async function fetchVaultProviderKeys(): Promise<{
  unlocked: boolean;
  resolved: Record<string, boolean>;
  dev_bypass: boolean;
}> {
  return vaultRequest('/api/vault/provider-keys');
}

export async function validateVaultSentry(): Promise<VaultSentryValidation> {
  return vaultRequest<VaultSentryValidation>('/api/vault/validate/sentry', {
    method: 'POST',
  });
}

export async function setupVault(masterPassword: string): Promise<VaultSetupResponse> {
  return vaultRequest<VaultSetupResponse>('/api/vault/setup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ master_password: masterPassword }),
  });
}

export async function unlockVault(
  masterPassword: string,
  totpCode: string,
  rememberMe = false,
): Promise<VaultUnlockResponse> {
  return vaultRequest<VaultUnlockResponse>('/api/vault/unlock', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      master_password: masterPassword,
      totp_code: totpCode,
      remember_me: rememberMe,
    }),
  });
}

export async function lockVault(): Promise<{ locked: boolean }> {
  return vaultRequest<{ locked: boolean }>('/api/vault/lock', { method: 'POST' });
}

export async function fetchVaultSecrets(): Promise<VaultSecretRecord[]> {
  return vaultRequest<VaultSecretRecord[]>('/api/vault/secrets');
}

export async function fetchVaultSecret(secretId: number): Promise<VaultSecretDetail> {
  return vaultRequest<VaultSecretDetail>(`/api/vault/secrets/${secretId}`);
}

export async function createVaultSecret(body: {
  name: string;
  category?: string;
  username?: string;
  password?: string;
  url?: string;
  notes?: string;
}): Promise<{ id: number; name: string }> {
  return vaultRequest('/api/vault/secrets', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export async function updateVaultSecret(
  secretId: number,
  body: {
    name: string;
    category?: string;
    username?: string;
    password?: string;
    url?: string;
    notes?: string;
  },
): Promise<{ updated: boolean }> {
  return vaultRequest(`/api/vault/secrets/${secretId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export async function deleteVaultSecret(secretId: number): Promise<{ deleted: boolean }> {
  return vaultRequest(`/api/vault/secrets/${secretId}`, { method: 'DELETE' });
}

export async function enableVaultAutoUnlock(): Promise<{ enabled: boolean; message: string }> {
  return vaultRequest('/api/vault/auto-unlock/enable', { method: 'POST' });
}

export async function disableVaultAutoUnlock(): Promise<{ enabled: boolean; removed: boolean }> {
  return vaultRequest('/api/vault/auto-unlock/disable', { method: 'POST' });
}

export async function importVaultSecrets(
  secrets: Record<string, string>,
  options: { exportText?: string } = {},
): Promise<VaultImportResponse> {
  return vaultRequest<VaultImportResponse>('/api/vault/import/monitor-keys', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      secrets,
      export_text: options.exportText ?? '',
    }),
  });
}

export async function importVaultBackupFile(
  file: File,
  options: { backupPassword?: string; mode?: 'merge' | 'replace' } = {},
): Promise<Record<string, unknown>> {
  const form = new FormData();
  form.append('file', file);
  form.append('backup_password', options.backupPassword ?? '');
  form.append('mode', options.mode ?? 'merge');
  return vaultRequest<Record<string, unknown>>('/api/vault/import', {
    method: 'POST',
    body: form,
  });
}

export async function exportVaultBackup(backupPassword: string): Promise<Blob> {
  return fetchBlob(
    '/api/vault/export',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ backup_password: backupPassword }),
    },
    'vault export failed',
  );
}

export async function exportVaultCsv(format: 'axon' | 'bitwarden' = 'axon'): Promise<Blob> {
  return fetchBlob(
    `/api/vault/export/csv?format=${format}`,
    {},
    'vault CSV export failed',
  );
}
