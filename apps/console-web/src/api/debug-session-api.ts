import { fetchJson } from './client';

export type DebugSessionLogEntry = {
  hypothesisId?: string;
  location?: string;
  message?: string;
  data?: Record<string, unknown>;
  timestamp?: number;
  [key: string]: unknown;
};

export type DebugSessionLogResponse = {
  ok: boolean;
  path: string;
  count: number;
  entries: DebugSessionLogEntry[];
};

export async function fetchDebugSessionLog(input: {
  workspaceId?: string | null;
  limit?: number;
}): Promise<DebugSessionLogResponse> {
  const params = new URLSearchParams();
  if (input.workspaceId?.trim()) {
    params.set('workspace_id', input.workspaceId.trim());
  }
  if (input.limit != null) {
    params.set('limit', String(input.limit));
  }
  const query = params.toString();
  return fetchJson<DebugSessionLogResponse>(
    `/api/dev/debug-session-log${query ? `?${query}` : ''}`,
    {},
    'debug session log request failed',
  );
}
