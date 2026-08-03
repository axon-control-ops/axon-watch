import type { RuntimeSummary } from '../contracts/canonical';

import { apiUrl, fetchJson, RUNTIME_STATUS_FETCH_TIMEOUT_MS } from './client';

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
  cursor_usage?: CursorUsageSnapshot | null;
}

export interface CursorUsageSnapshot {
  ok: boolean;
  source?: string;
  updated_at?: string;
  membership_type?: string | null;
  subscription_status?: string | null;
  on_demand_enabled?: boolean | null;
  auto_percent_used?: number | null;
  api_percent_used?: number | null;
  total_percent_used?: number | null;
  display_message?: string | null;
  auto_display_message?: string | null;
  api_display_message?: string | null;
  message?: string | null;
  allows_agent_retry?: boolean;
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

export interface CodexRuntimeStatusSnapshot {
  installed: boolean;
  binary: string;
  auth: RuntimeAuthStatus;
  available_models: CursorModelRecord[];
  codex_models: CursorModelRecord[];
  catalog_source: 'live' | 'unavailable' | string;
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

export interface RuntimeAuthActionResult {
  status: 'completed' | 'browser_opened' | 'manual_required' | 'error' | string;
  message: string;
  command_preview?: string;
  output?: string;
  runtime_status?: RuntimeStatusSnapshot;
  cursor_runtime?: CursorRuntimeStatusSnapshot;
}

export interface ReadinessSnapshot {
  service: string;
  status: string;
  mode?: string;
  watch_base_url?: string;
  state_dir?: string;
  public_base_url?: string;
}

export async function fetchRuntimeSummary(): Promise<RuntimeSummary> {
  return fetchJson<RuntimeSummary>('/api/runtime/summary', {}, 'runtime summary request failed');
}

export async function fetchRuntimeStatus(
  options: { forceRefresh?: boolean } = {},
): Promise<RuntimeStatusSnapshot> {
  const query = options.forceRefresh ? '?force_refresh=1' : '';
  return fetchJson<RuntimeStatusSnapshot>(
    `/api/runtime/status${query}`,
    {},
    'runtime status request failed',
    RUNTIME_STATUS_FETCH_TIMEOUT_MS,
  );
}

export async function fetchRuntimeMcpTools(): Promise<RuntimeMcpToolsSnapshot> {
  return fetchJson<RuntimeMcpToolsSnapshot>(
    '/api/runtime/mcp-tools',
    {},
    'runtime mcp-tools request failed',
  );
}

export async function fetchCursorRuntimeStatus(
  options: { forceRefresh?: boolean } = {},
): Promise<CursorRuntimeStatusSnapshot> {
  const query = options.forceRefresh ? '?force_refresh=1' : '';
  return fetchJson<CursorRuntimeStatusSnapshot>(
    `/api/runtime/cursor/status${query}`,
    {},
    'cursor runtime status request failed',
    RUNTIME_STATUS_FETCH_TIMEOUT_MS,
  );
}

export async function fetchCodexRuntimeStatus(
  options: { forceRefresh?: boolean } = {},
): Promise<CodexRuntimeStatusSnapshot> {
  const query = options.forceRefresh ? '?force_refresh=1' : '';
  return fetchJson<CodexRuntimeStatusSnapshot>(
    `/api/runtime/codex/status${query}`,
    {},
    'Codex model catalog request failed',
    RUNTIME_STATUS_FETCH_TIMEOUT_MS,
  );
}

async function postRuntimeAuthAction(path: string): Promise<RuntimeAuthActionResult> {
  return fetchJson<RuntimeAuthActionResult>(
    path,
    { method: 'POST' },
    'runtime auth action failed',
    RUNTIME_STATUS_FETCH_TIMEOUT_MS,
  );
}

export function logoutCursorRuntime(): Promise<RuntimeAuthActionResult> {
  return postRuntimeAuthAction('/api/runtime/cursor/logout');
}

export function startCursorRuntimeLogin(): Promise<RuntimeAuthActionResult> {
  return postRuntimeAuthAction('/api/runtime/cursor/login/start');
}

export function logoutCodexRuntime(): Promise<RuntimeAuthActionResult> {
  return postRuntimeAuthAction('/api/runtime/codex/logout');
}

export function startCodexRuntimeLogin(): Promise<RuntimeAuthActionResult> {
  return postRuntimeAuthAction('/api/runtime/codex/login/start');
}

export function logoutClaudeRuntime(): Promise<RuntimeAuthActionResult> {
  return postRuntimeAuthAction('/api/runtime/claude/logout');
}

export function startClaudeRuntimeLogin(): Promise<RuntimeAuthActionResult> {
  return postRuntimeAuthAction('/api/runtime/claude/login/start');
}

export async function fetchReadiness(): Promise<ReadinessSnapshot> {
  return fetchJson<ReadinessSnapshot>('/api/readiness', {}, 'readiness request failed');
}
