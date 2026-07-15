/** Lightweight NDJSON debug-session logger for evidence-first bug hunts. */

import { apiUrl } from '../api/client';

export type AxonDebugSessionEvent = {
  hypothesisId: string;
  location: string;
  message: string;
  data?: Record<string, unknown>;
  timestamp?: number;
  workspaceId?: string;
};

export function axonDebugSessionLog(event: AxonDebugSessionEvent): void {
  if (import.meta.env.PROD || import.meta.env.VITE_AXON_DEBUG_SESSION_LOG !== '1') {
    return;
  }
  const payload = {
    hypothesisId: event.hypothesisId,
    location: event.location,
    message: event.message,
    data: event.data ?? {},
    timestamp: event.timestamp ?? Date.now(),
    // Prefer axon-local Cursor project root for this debug hunt unless overridden.
    workspace_id: event.workspaceId ?? 'workspace_axon_local',
  };
  void fetch(apiUrl('/api/dev/debug-session-log'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }).catch(() => {});
}
