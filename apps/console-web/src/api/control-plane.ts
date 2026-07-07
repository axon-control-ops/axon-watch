import type {
  InboxItem,
  OperatorBriefing,
  OperatorPresenceSettings,
  RunRecord,
  RuntimeSummary,
  WorkspaceRecord,
} from '../contracts/canonical';

import type { BrainGraphSnapshot } from '../lib/operator-brain-graph-view';
import type { RunHistorySnapshot } from '../lib/run-history-view';
import type {
  VaultSecretDetail,
  VaultSecretRecord,
  VaultStatusSnapshot,
} from '../lib/vault-surface-view';

export interface InboxSnapshot {
  items: InboxItem[];
  count: number;
  updated_at: string;
}

export interface RunListSnapshot {
  items: RunRecord[];
  count: number;
}

export interface WorkspaceListSnapshot {
  items: WorkspaceRecord[];
  count: number;
}

export interface CreateRunRequest {
  workspace_id: string;
  mode?: RunRecord['mode'];
  summary: string;
  detail?: string;
  requires_approval?: boolean;
}

export interface RuntimeAuthStatus {
  logged_in?: boolean;
  auth_method?: string;
  provider_label?: string;
  account_label?: string;
  message?: string;
  vault_posture?: 'ready' | 'vault_locked' | 'missing_keys' | string;
}

export interface RuntimeVaultPosture {
  unlocked: boolean;
  posture: 'ready' | 'vault_locked' | 'missing_keys' | string;
  hint?: string;
  runtime_keys?: Record<string, boolean>;
  provider_keys?: Record<string, boolean>;
}

export interface RuntimeTargetRecord {
  id: string;
  family: string;
  label: string;
  target_type: 'local' | 'cloud' | string;
  available: boolean;
  binary: string;
  auth: RuntimeAuthStatus;
  ready: boolean;
  mode_support: string[];
  recommended?: boolean;
}

export interface RuntimeStatusSnapshot {
  updated_at: string;
  default_runtime: string;
  vault_runtime?: RuntimeVaultPosture;
  local: RuntimeTargetRecord[];
  cloud: RuntimeTargetRecord[];
}

export interface CursorModelRecord {
  id: string;
  label: string;
  description?: string;
  badge?: string;
  available?: boolean;
}

export interface CursorRuntimeStatusSnapshot {
  installed: boolean;
  binary: string;
  auth: RuntimeAuthStatus;
  available_models: CursorModelRecord[];
  cursor_models: CursorModelRecord[];
  catalog_source: 'live' | 'fallback' | string;
}

function controlPlaneBaseUrl(): string {
  const configured = import.meta.env.VITE_CONTROL_PLANE_BASE_URL;
  if (configured) {
    return configured.replace(/\/$/, '');
  }

  return '';
}

export async function fetchRuntimeSummary(): Promise<RuntimeSummary> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/runtime/summary` : '/api/runtime/summary';
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`runtime summary request failed with status ${response.status}`);
  }

  return response.json() as Promise<RuntimeSummary>;
}

export async function fetchRuntimeStatus(): Promise<RuntimeStatusSnapshot> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/runtime/status` : '/api/runtime/status';
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`runtime status request failed with status ${response.status}`);
  }

  return response.json() as Promise<RuntimeStatusSnapshot>;
}

export interface RuntimeMcpToolRecord {
  id: string;
  label: string;
  bounded_context: string;
  mode_support: string[];
}

export interface RuntimeMcpToolsSnapshot {
  count: number;
  items: RuntimeMcpToolRecord[];
}

export async function fetchRuntimeMcpTools(): Promise<RuntimeMcpToolsSnapshot> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/runtime/mcp-tools` : '/api/runtime/mcp-tools';
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`runtime mcp-tools request failed with status ${response.status}`);
  }

  return response.json() as Promise<RuntimeMcpToolsSnapshot>;
}

export async function fetchCursorRuntimeStatus(
  options: { forceRefresh?: boolean } = {},
): Promise<CursorRuntimeStatusSnapshot> {
  const baseUrl = controlPlaneBaseUrl();
  const query = options.forceRefresh ? '?force_refresh=1' : '';
  const url = baseUrl
    ? `${baseUrl}/api/runtime/cursor/status${query}`
    : `/api/runtime/cursor/status${query}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`cursor runtime status request failed with status ${response.status}`);
  }

  return response.json() as Promise<CursorRuntimeStatusSnapshot>;
}

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
): Promise<T> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}${path}` : path;
  const response = await fetch(url, init);
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
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/vault/import` : '/api/vault/import';
  const form = new FormData();
  form.append('file', file);
  form.append('backup_password', options.backupPassword ?? '');
  form.append('mode', options.mode ?? 'merge');
  const response = await fetch(url, { method: 'POST', body: form });
  if (!response.ok) {
    throw new Error(`vault backup import failed with status ${response.status}`);
  }
  return response.json() as Promise<Record<string, unknown>>;
}

export async function exportVaultBackup(backupPassword: string): Promise<Blob> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/vault/export` : '/api/vault/export';
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ backup_password: backupPassword }),
  });
  if (!response.ok) {
    throw new Error(`vault export failed with status ${response.status}`);
  }
  return response.blob();
}

export async function exportVaultCsv(format: 'axon' | 'bitwarden' = 'axon'): Promise<Blob> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl
    ? `${baseUrl}/api/vault/export/csv?format=${format}`
    : `/api/vault/export/csv?format=${format}`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`vault CSV export failed with status ${response.status}`);
  }
  return response.blob();
}

export interface OperatorDataSnapshotResponse {
  data: {
    updated_at: string;
    control_plane: {
      runs: { total: number; count: number; items: Record<string, unknown>[] };
      chat_threads: { total: number; count: number; items: Record<string, unknown>[] };
      chat_messages: { total: number; count: number; items: Record<string, unknown>[] };
      handoffs: { total: number; count: number; items: Record<string, unknown>[] };
    };
    watch: Record<string, { total: number; count: number; items: Record<string, unknown>[] }>;
  };
}

export async function fetchDataSnapshot(): Promise<OperatorDataSnapshotResponse> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/data/snapshot` : '/api/data/snapshot';
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`data snapshot request failed with status ${response.status}`);
  }

  return response.json() as Promise<OperatorDataSnapshotResponse>;
}

export async function downloadDataExport(): Promise<Blob> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/data/export` : '/api/data/export';
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`data export request failed with status ${response.status}`);
  }

  return response.blob();
}

export async function fetchInbox(): Promise<InboxSnapshot> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/inbox` : '/api/inbox';
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`inbox request failed with status ${response.status}`);
  }

  return response.json() as Promise<InboxSnapshot>;
}

export interface AcknowledgeInboxSignalsResult {
  accepted: boolean;
  acknowledged: string[];
  count: number;
  command_id?: string;
  status?: string;
}

export async function acknowledgeInboxSignals(
  signalIds: string[],
): Promise<AcknowledgeInboxSignalsResult> {
  const baseUrl = controlPlaneBaseUrl();
  const dedicatedUrl = baseUrl
    ? `${baseUrl}/api/inbox/signals/acknowledge`
    : '/api/inbox/signals/acknowledge';
  const response = await fetch(dedicatedUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ signal_ids: signalIds }),
  });

  if (response.status === 404) {
    return acknowledgeInboxSignalsViaWatchCommand(signalIds);
  }

  if (!response.ok) {
    throw new Error(`signal acknowledge request failed with status ${response.status}`);
  }

  return response.json() as Promise<AcknowledgeInboxSignalsResult>;
}

export interface CreateWorkspaceHandoffRequest {
  target_workspace_id: string;
  task: string;
  reason?: string;
}

export interface WorkspaceHandoffCreateResponse {
  handoff: Record<string, unknown>;
  target_workspace: WorkspaceRecord;
  target_workspace_summary: Record<string, unknown>;
}

export async function createWorkspaceHandoff(
  sourceWorkspaceId: string,
  body: CreateWorkspaceHandoffRequest,
): Promise<WorkspaceHandoffCreateResponse> {
  const baseUrl = controlPlaneBaseUrl();
  const encoded = encodeURIComponent(sourceWorkspaceId);
  const url = baseUrl
    ? `${baseUrl}/api/workspaces/${encoded}/handoffs`
    : `/api/workspaces/${encoded}/handoffs`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`workspace handoff failed with status ${response.status}`);
  }
  return response.json() as Promise<WorkspaceHandoffCreateResponse>;
}

async function acknowledgeInboxSignalsViaWatchCommand(
  signalIds: string[],
): Promise<AcknowledgeInboxSignalsResult> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/watch/commands` : '/api/watch/commands';
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      command_type: 'acknowledge_signal',
      target_type: 'signal',
      requested_by: 'operator',
      payload: { signal_ids: signalIds },
    }),
  });

  if (!response.ok) {
    if (response.status === 400 || response.status === 503) {
      throw new Error(
        'Signal clear is unavailable until services restart: ./scripts/dev/down.sh && ./scripts/dev/up.sh',
      );
    }
    throw new Error(`signal acknowledge request failed with status ${response.status}`);
  }

  const payload = (await response.json()) as {
    accepted?: boolean;
    command_id?: string;
    status?: string;
    receipt?: {
      result?: {
        acknowledged?: string[];
        count?: number;
      };
    };
  };
  const result = payload.receipt?.result;
  const acknowledged = Array.isArray(result?.acknowledged) ? result.acknowledged : [];

  return {
    accepted: Boolean(payload.accepted),
    acknowledged,
    count: typeof result?.count === 'number' ? result.count : acknowledged.length,
    command_id: payload.command_id,
    status: payload.status,
  };
}

export async function fetchOperatorBriefing(options?: {
  viewportCompact?: boolean;
  workspaceId?: string | null;
}): Promise<OperatorBriefing> {
  const baseUrl = controlPlaneBaseUrl();
  const compact = Boolean(options?.viewportCompact);
  const params = new URLSearchParams();
  if (compact) {
    params.set('viewport_compact', 'true');
  }
  const workspaceId = options?.workspaceId?.trim();
  if (workspaceId) {
    params.set('workspace_id', workspaceId);
  }
  const query = params.size > 0 ? `?${params.toString()}` : '';
  const url = baseUrl ? `${baseUrl}/api/briefing${query}` : `/api/briefing${query}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`operator briefing request failed with status ${response.status}`);
  }

  return response.json() as Promise<OperatorBriefing>;
}

export type FleetHealthSnapshot = {
  generated_at: string;
  watch_connected: boolean;
  connectors: RuntimeSummary['connectors'];
  degraded: RuntimeSummary['degraded'];
  items: Array<{
    workspace_id: string;
    display_name: string;
    connection_kind: string;
    health: 'nominal' | 'attention' | 'critical';
    active_runs: number;
    review_ready_count: number;
    executing_count: number;
    pending_approvals_count: number;
    open_signals_count: number;
    critical_signals_count: number;
    top_signal_title: string | null;
  }>;
  count: number;
};

export async function fetchOperatorFleetHealth(): Promise<FleetHealthSnapshot> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/operator/fleet-health` : '/api/operator/fleet-health';
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`operator fleet health request failed with status ${response.status}`);
  }

  return response.json() as Promise<FleetHealthSnapshot>;
}

export async function fetchOperatorBrainGraph(): Promise<BrainGraphSnapshot> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/operator/brain-graph` : '/api/operator/brain-graph';
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`operator brain graph request failed with status ${response.status}`);
  }

  return response.json() as Promise<BrainGraphSnapshot>;
}

export interface OperatorPresenceSettingsSnapshot {
  settings: OperatorPresenceSettings;
  updated_at?: string;
}

export async function fetchOperatorPresenceSettings(): Promise<OperatorPresenceSettingsSnapshot> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl
    ? `${baseUrl}/api/operator-presence/settings`
    : '/api/operator-presence/settings';
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`operator presence settings request failed with status ${response.status}`);
  }

  return response.json() as Promise<OperatorPresenceSettingsSnapshot>;
}

export async function saveOperatorPresenceSettings(
  patch: Partial<OperatorPresenceSettings>,
): Promise<OperatorPresenceSettingsSnapshot> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl
    ? `${baseUrl}/api/operator-presence/settings`
    : '/api/operator-presence/settings';
  const response = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  });

  if (!response.ok) {
    throw new Error(`operator presence settings save failed with status ${response.status}`);
  }

  return response.json() as Promise<OperatorPresenceSettingsSnapshot>;
}

export async function fetchRuns(): Promise<RunListSnapshot> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/runs` : '/api/runs';
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`runs request failed with status ${response.status}`);
  }

  return response.json() as Promise<RunListSnapshot>;
}

export async function fetchWorkspaces(options?: {
  scope?: 'all' | 'operator';
}): Promise<WorkspaceListSnapshot> {
  const baseUrl = controlPlaneBaseUrl();
  const scope = options?.scope === 'operator' ? 'operator' : '';
  const query = scope ? '?scope=operator' : '';
  const url = baseUrl ? `${baseUrl}/api/workspaces${query}` : `/api/workspaces${query}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`workspaces request failed with status ${response.status}`);
  }

  return response.json() as Promise<WorkspaceListSnapshot>;
}

export async function fetchWorkspace(workspaceId: string): Promise<WorkspaceRecord> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/workspaces/${workspaceId}` : `/api/workspaces/${workspaceId}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`workspace request failed with status ${response.status}`);
  }

  return response.json() as Promise<WorkspaceRecord>;
}

export async function fetchRun(runId: string): Promise<RunRecord> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/runs/${runId}` : `/api/runs/${runId}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`run request failed with status ${response.status}`);
  }

  return response.json() as Promise<RunRecord>;
}

export async function fetchRunHistory(runId: string): Promise<RunHistorySnapshot> {
  const baseUrl = controlPlaneBaseUrl();
  const encodedRunId = encodeURIComponent(runId);
  const url = baseUrl
    ? `${baseUrl}/api/runs/${encodedRunId}/history`
    : `/api/runs/${encodedRunId}/history`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`run history request failed with status ${response.status}`);
  }

  return response.json() as Promise<RunHistorySnapshot>;
}

export async function createRun(body: CreateRunRequest): Promise<RunRecord> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/runs` : '/api/runs';
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`create run request failed with status ${response.status}`);
  }

  return response.json() as Promise<RunRecord>;
}

export async function completeRun(runId: string): Promise<RunRecord> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/runs/${runId}/complete` : `/api/runs/${runId}/complete`;
  const response = await fetch(url, { method: 'POST' });

  if (!response.ok) {
    throw new Error(`complete run request failed with status ${response.status}`);
  }

  return response.json() as Promise<RunRecord>;
}

export async function markRunReviewReady(runId: string): Promise<RunRecord> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/runs/${runId}/review-ready` : `/api/runs/${runId}/review-ready`;
  const response = await fetch(url, { method: 'POST' });

  if (!response.ok) {
    throw new Error(`review-ready request failed with status ${response.status}`);
  }

  return response.json() as Promise<RunRecord>;
}

export async function stopRun(runId: string): Promise<RunRecord> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/runs/${runId}/stop` : `/api/runs/${runId}/stop`;
  const response = await fetch(url, { method: 'POST' });

  if (!response.ok) {
    throw new Error(`stop run request failed with status ${response.status}`);
  }

  return response.json() as Promise<RunRecord>;
}

export async function resumeRun(runId: string): Promise<RunRecord> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/runs/${runId}/resume` : `/api/runs/${runId}/resume`;
  const response = await fetch(url, { method: 'POST' });

  if (!response.ok) {
    throw new Error(`resume run request failed with status ${response.status}`);
  }

  return response.json() as Promise<RunRecord>;
}

export async function approveRun(runId: string): Promise<RunRecord> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/runs/${runId}/approve` : `/api/runs/${runId}/approve`;
  const response = await fetch(url, { method: 'POST' });

  if (!response.ok) {
    throw new Error(`approve run request failed with status ${response.status}`);
  }

  return response.json() as Promise<RunRecord>;
}

export async function rejectRun(runId: string): Promise<RunRecord> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/runs/${runId}/reject` : `/api/runs/${runId}/reject`;
  const response = await fetch(url, { method: 'POST' });

  if (!response.ok) {
    throw new Error(`reject run request failed with status ${response.status}`);
  }

  return response.json() as Promise<RunRecord>;
}

export interface WorkspaceFileEntry {
  path: string;
  size_bytes: number;
}

export interface WorkspaceFileListSnapshot {
  workspace_id: string;
  items: WorkspaceFileEntry[];
  count: number;
}

export interface WorkspaceFileContent {
  workspace_id: string;
  path: string;
  content: string;
  size_bytes: number;
}

export interface WorkspaceFileRenameResponse {
  workspace_id: string;
  old_path: string;
  path: string;
  size_bytes: number;
  renamed: boolean;
}

export async function fetchWorkspaceFiles(workspaceId: string): Promise<WorkspaceFileListSnapshot> {
  const baseUrl = controlPlaneBaseUrl();
  const encoded = encodeURIComponent(workspaceId);
  const url = baseUrl
    ? `${baseUrl}/api/workspaces/${encoded}/files`
    : `/api/workspaces/${encoded}/files`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`workspace files request failed with status ${response.status}`);
  }

  return response.json() as Promise<WorkspaceFileListSnapshot>;
}

export async function fetchWorkspaceFile(
  workspaceId: string,
  filePath: string,
): Promise<WorkspaceFileContent> {
  const baseUrl = controlPlaneBaseUrl();
  const encodedWorkspace = encodeURIComponent(workspaceId);
  const encodedPath = filePath
    .split('/')
    .map((segment) => encodeURIComponent(segment))
    .join('/');
  const url = baseUrl
    ? `${baseUrl}/api/workspaces/${encodedWorkspace}/files/${encodedPath}`
    : `/api/workspaces/${encodedWorkspace}/files/${encodedPath}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`workspace file read failed with status ${response.status}`);
  }

  return response.json() as Promise<WorkspaceFileContent>;
}

export async function saveWorkspaceFile(
  workspaceId: string,
  filePath: string,
  content: string,
): Promise<{ saved: boolean; path: string; size_bytes: number }> {
  const baseUrl = controlPlaneBaseUrl();
  const encodedWorkspace = encodeURIComponent(workspaceId);
  const encodedPath = filePath
    .split('/')
    .map((segment) => encodeURIComponent(segment))
    .join('/');
  const url = baseUrl
    ? `${baseUrl}/api/workspaces/${encodedWorkspace}/files/${encodedPath}`
    : `/api/workspaces/${encodedWorkspace}/files/${encodedPath}`;
  const response = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  });

  if (!response.ok) {
    throw new Error(`workspace file save failed with status ${response.status}`);
  }

  return response.json() as Promise<{ saved: boolean; path: string; size_bytes: number }>;
}

export async function renameWorkspaceFile(
  workspaceId: string,
  filePath: string,
  newPath: string,
): Promise<WorkspaceFileRenameResponse> {
  const baseUrl = controlPlaneBaseUrl();
  const encodedWorkspace = encodeURIComponent(workspaceId);
  const encodedPath = filePath
    .split('/')
    .map((segment) => encodeURIComponent(segment))
    .join('/');
  const url = baseUrl
    ? `${baseUrl}/api/workspaces/${encodedWorkspace}/files/${encodedPath}/rename`
    : `/api/workspaces/${encodedWorkspace}/files/${encodedPath}/rename`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ new_path: newPath }),
  });

  if (!response.ok) {
    throw new Error(`workspace file rename failed with status ${response.status}`);
  }

  return response.json() as Promise<WorkspaceFileRenameResponse>;
}

export interface ChatAttachmentRecord {
  attachment_id: string;
  workspace_id: string;
  message_id?: string | null;
  thread_id?: string | null;
  filename: string;
  mime_type: string;
  url: string;
  created_at: string;
}

export interface ChatMessageRecord {
  message_id: string;
  thread_id: string;
  run_id: string | null;
  workspace_id: string | null;
  role: 'operator' | 'system' | string;
  content: string;
  created_at: string;
  attachments?: ChatAttachmentRecord[];
}

export interface EditorSelectionContext {
  file_path: string;
  start_line: number;
  end_line: number;
  text: string;
}

export interface PostChatMessageRequest {
  workspace_id: string;
  content: string;
  thread_id?: string | null;
  run_id?: string | null;
  composer_mode?: 'ask' | 'plan' | 'agent' | 'command' | string | null;
  active_file_path?: string | null;
  editor_selection?: EditorSelectionContext | null;
  terminal_snippet?: string | null;
  attachment_ids?: string[] | null;
  runtime_target?: string | null;
  runtime_model?: string | null;
  execution_access?: 'consultative' | 'full' | string | null;
}

import type { ChatUiAction } from '../lib/chat-ui-action';

export interface PostChatMessageResponse {
  thread_id: string;
  messages: ChatMessageRecord[];
  run_id: string;
  dispatched: boolean;
  run: RunRecord | null;
  streaming?: boolean;
  stream_agent_message_id?: string;
  ui_action?: ChatUiAction | null;
  agent_terminal_session?: TerminalSessionRecord | null;
}

export interface TerminalSessionRecord {
  session_id: string;
  workspace_id: string;
  role: 'operator' | 'agent' | string;
  title: string;
  run_id: string | null;
  created_at: string;
}

export interface WorkspaceChatThreadListItem {
  thread_id: string;
  workspace_id: string;
  run_id: string | null;
  thread_kind: string;
  created_at: string;
  updated_at: string;
  preview_label: string;
}

export interface WorkspaceChatThreadListSnapshot {
  workspace_id: string;
  thread_kind: string;
  items: WorkspaceChatThreadListItem[];
  count: number;
}

export interface ThreadHistorySnapshot {
  thread_id: string;
  workspace_id: string;
  run_id: string | null;
  items: ChatMessageRecord[];
  count: number;
}

export interface WorkspaceChatThreadSnapshot {
  thread_id: string | null;
  workspace_id: string;
  run_id: string | null;
  updated_at: string | null;
}

export function hasWorkspaceChatThread(
  snapshot: WorkspaceChatThreadSnapshot,
): snapshot is WorkspaceChatThreadSnapshot & { thread_id: string } {
  return snapshot.thread_id !== null;
}

export async function postChatMessage(
  body: PostChatMessageRequest,
): Promise<PostChatMessageResponse> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/chat/messages` : '/api/chat/messages';
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`chat message submit failed with status ${response.status}`);
  }

  return response.json() as Promise<PostChatMessageResponse>;
}

export async function fetchThreadHistory(threadId: string): Promise<ThreadHistorySnapshot> {
  const baseUrl = controlPlaneBaseUrl();
  const encodedThreadId = encodeURIComponent(threadId);
  const url = baseUrl
    ? `${baseUrl}/api/chat/threads/${encodedThreadId}/history`
    : `/api/chat/threads/${encodedThreadId}/history`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`thread history fetch failed with status ${response.status}`);
  }

  return response.json() as Promise<ThreadHistorySnapshot>;
}

export async function fetchWorkspaceChatThread(
  workspaceId: string,
  options: { surface?: 'operator' | 'ide' } = {},
): Promise<WorkspaceChatThreadSnapshot> {
  const baseUrl = controlPlaneBaseUrl();
  const encodedWorkspaceId = encodeURIComponent(workspaceId);
  const surface = options.surface ?? 'operator';
  const query = `?surface=${encodeURIComponent(surface)}`;
  const url = baseUrl
    ? `${baseUrl}/api/workspaces/${encodedWorkspaceId}/chat/thread${query}`
    : `/api/workspaces/${encodedWorkspaceId}/chat/thread${query}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`workspace chat thread lookup failed with status ${response.status}`);
  }

  return response.json() as Promise<WorkspaceChatThreadSnapshot>;
}

export async function uploadChatAttachment(
  workspaceId: string,
  file: File,
): Promise<ChatAttachmentRecord> {
  const baseUrl = controlPlaneBaseUrl();
  const encodedWorkspaceId = encodeURIComponent(workspaceId);
  const url = baseUrl
    ? `${baseUrl}/api/chat/attachments`
    : '/api/chat/attachments';
  const formData = new FormData();
  formData.append('workspace_id', workspaceId);
  formData.append('file', file, file.name);

  const response = await fetch(url, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`chat attachment upload failed with status ${response.status}`);
  }

  return response.json() as Promise<ChatAttachmentRecord>;
}

export async function fetchWorkspaceChatThreads(
  workspaceId: string,
  options: { surface?: 'operator' | 'ide'; limit?: number } = {},
): Promise<WorkspaceChatThreadListSnapshot> {
  const baseUrl = controlPlaneBaseUrl();
  const encodedWorkspaceId = encodeURIComponent(workspaceId);
  const surface = options.surface ?? 'ide';
  const limit = options.limit ?? 25;
  const query = `?surface=${encodeURIComponent(surface)}&limit=${encodeURIComponent(String(limit))}`;
  const url = baseUrl
    ? `${baseUrl}/api/workspaces/${encodedWorkspaceId}/chat/threads${query}`
    : `/api/workspaces/${encodedWorkspaceId}/chat/threads${query}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`workspace chat thread list failed with status ${response.status}`);
  }

  return response.json() as Promise<WorkspaceChatThreadListSnapshot>;
}

export async function createWorkspaceChatThread(
  workspaceId: string,
  options: { surface?: 'operator' | 'ide'; runId?: string | null } = {},
): Promise<WorkspaceChatThreadListItem> {
  const baseUrl = controlPlaneBaseUrl();
  const encodedWorkspaceId = encodeURIComponent(workspaceId);
  const url = baseUrl
    ? `${baseUrl}/api/workspaces/${encodedWorkspaceId}/chat/threads`
    : `/api/workspaces/${encodedWorkspaceId}/chat/threads`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      surface: options.surface ?? 'ide',
      run_id: options.runId ?? null,
    }),
  });

  if (!response.ok) {
    throw new Error(`workspace chat thread create failed with status ${response.status}`);
  }

  return response.json() as Promise<WorkspaceChatThreadListItem>;
}

export async function fetchWorkspaceTerminalSessions(
  workspaceId: string,
): Promise<{ workspace_id: string; items: TerminalSessionRecord[]; count: number }> {
  const baseUrl = controlPlaneBaseUrl();
  const encodedWorkspaceId = encodeURIComponent(workspaceId);
  const url = baseUrl
    ? `${baseUrl}/api/workspaces/${encodedWorkspaceId}/terminal/sessions`
    : `/api/workspaces/${encodedWorkspaceId}/terminal/sessions`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`workspace terminal sessions failed with status ${response.status}`);
  }

  return response.json() as Promise<{
    workspace_id: string;
    items: TerminalSessionRecord[];
    count: number;
  }>;
}

export async function createWorkspaceTerminalSession(
  workspaceId: string,
  options: {
    role?: 'operator' | 'agent' | string;
    title?: string | null;
    runId?: string | null;
    sessionId?: string | null;
  } = {},
): Promise<TerminalSessionRecord> {
  const baseUrl = controlPlaneBaseUrl();
  const encodedWorkspaceId = encodeURIComponent(workspaceId);
  const url = baseUrl
    ? `${baseUrl}/api/workspaces/${encodedWorkspaceId}/terminal/sessions`
    : `/api/workspaces/${encodedWorkspaceId}/terminal/sessions`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      role: options.role ?? 'operator',
      title: options.title ?? null,
      run_id: options.runId ?? null,
      session_id: options.sessionId ?? null,
    }),
  });

  if (!response.ok) {
    throw new Error(`workspace terminal session create failed with status ${response.status}`);
  }

  return response.json() as Promise<TerminalSessionRecord>;
}

export interface ConnectorProbeRecord {
  connector_id: string;
  display_name: string;
  status: string;
  required: boolean;
  workspace_id?: string;
  health_url?: string;
  detail?: string;
  latency_ms?: number;
  last_checked_at?: string;
  tunnel?: {
    mode?: string;
    tunnel_url?: string;
    process_running?: boolean;
    auth_ready?: boolean;
    binary_path?: string;
  };
}

export interface TunnelStatusSnapshot {
  running: boolean;
  url: string;
  mode: string;
  named_tunnel_ready: boolean;
  auth_source: string;
  binary_path: string;
  status: string;
  detail: string;
  msg?: string;
}

export interface ConnectorsSnapshot {
  count: number;
  summary: {
    configured: number;
    ok: number;
    degraded: number;
    unavailable: number;
    required_unavailable: number;
    last_updated_at?: string;
  };
  items: ConnectorProbeRecord[];
}

export async function fetchConnectors(): Promise<ConnectorsSnapshot> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/connectors` : '/api/connectors';
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`connectors request failed with status ${response.status}`);
  }

  return response.json() as Promise<ConnectorsSnapshot>;
}

export async function fetchTunnelStatus(): Promise<TunnelStatusSnapshot> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/tunnel/status` : '/api/tunnel/status';
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`tunnel status request failed with status ${response.status}`);
  }

  return response.json() as Promise<TunnelStatusSnapshot>;
}

export async function startTunnel(): Promise<TunnelStatusSnapshot> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/tunnel/start` : '/api/tunnel/start';
  const response = await fetch(url, { method: 'POST' });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `tunnel start failed with status ${response.status}`);
  }

  return response.json() as Promise<TunnelStatusSnapshot>;
}

export async function stopTunnel(): Promise<TunnelStatusSnapshot> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/tunnel/stop` : '/api/tunnel/stop';
  const response = await fetch(url, { method: 'POST' });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `tunnel stop failed with status ${response.status}`);
  }

  return response.json() as Promise<TunnelStatusSnapshot>;
}

export interface PostWatchCommandRequest {
  command_type: string;
  target_type?: string;
  target_id?: string;
  requested_by?: string;
  payload?: Record<string, unknown>;
}

export interface PostWatchCommandResponse {
  accepted?: boolean;
  command_id?: string;
  status?: string;
  receipt?: {
    result?: Record<string, unknown>;
  };
}

export async function postWatchCommand(
  body: PostWatchCommandRequest,
): Promise<PostWatchCommandResponse> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/watch/commands` : '/api/watch/commands';
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`watch command request failed with status ${response.status}`);
  }

  return response.json() as Promise<PostWatchCommandResponse>;
}

export const LEGACY_AXON_LOCAL_FALLBACK_URL = 'http://127.0.0.1:7734';
