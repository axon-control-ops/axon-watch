import { apiUrl, fetchJson } from './client';

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
    control_backend?: string;
    managed_process?: boolean;
    managed_pid?: number | null;
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
  control_backend: string;
  managed: boolean;
  pid: number | null;
  process_state_path: string;
  log_path: string;
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

export async function fetchConnectors(): Promise<ConnectorsSnapshot> {
  return fetchJson<ConnectorsSnapshot>('/api/connectors', {}, 'connectors request failed');
}

export async function fetchTunnelStatus(): Promise<TunnelStatusSnapshot> {
  return fetchJson<TunnelStatusSnapshot>('/api/tunnel/status', {}, 'tunnel status request failed');
}

export async function startTunnel(): Promise<TunnelStatusSnapshot> {
  const response = await fetch(apiUrl('/api/tunnel/start'), { method: 'POST' });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `tunnel start failed with status ${response.status}`);
  }
  return response.json() as Promise<TunnelStatusSnapshot>;
}

export async function stopTunnel(): Promise<TunnelStatusSnapshot> {
  const response = await fetch(apiUrl('/api/tunnel/stop'), { method: 'POST' });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `tunnel stop failed with status ${response.status}`);
  }
  return response.json() as Promise<TunnelStatusSnapshot>;
}

export async function postWatchCommand(
  body: PostWatchCommandRequest,
): Promise<PostWatchCommandResponse> {
  return fetchJson<PostWatchCommandResponse>(
    '/api/watch/commands',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
    'watch command request failed',
  );
}

/** Explicit fallback URL when the axon_local connector row is shown. */
export const LEGACY_AXON_LOCAL_FALLBACK_URL = 'http://127.0.0.1:7734';
