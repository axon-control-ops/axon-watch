import { fetchJson } from './client';

export type RecoveryAction = {
  action: string;
  authority: string;
  summary: string;
  safe: boolean;
};

export type RecoveryCenterItem = {
  recovery_id?: string;
  acknowledged?: boolean;
  actionable?: boolean;
  run_id: string;
  task_id: string | null;
  workspace_id: string;
  agent: string;
  phase: string;
  bucket: string;
  failure_class: string;
  what_happened: string;
  why_stale: string;
  last_meaningful_progress: string | null;
  last_heartbeat: string | null;
  current_worker: string | null;
  current_lease: Record<string, unknown> | null;
  current_checkpoint: Record<string, unknown> | null;
  files_changed: string[];
  last_known_provider: string;
  retry_count: number;
  recovery_action: RecoveryAction;
  evidence: Record<string, unknown>;
  actions: string[];
};

export type RecoveryCenterSnapshot = {
  generated_at: string;
  attention_count: number;
  counts: Record<string, number>;
  items: RecoveryCenterItem[];
};

export async function fetchRecoveryCenter(workspaceId?: string | null): Promise<RecoveryCenterSnapshot> {
  const query = workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : '';
  return fetchJson<RecoveryCenterSnapshot>(
    `/api/recovery/center${query}`,
    { method: 'GET' },
    'recovery center failed',
  );
}

export async function fetchOperationalInstructions(body: {
  workspace_id: string;
  run_id?: string | null;
  agent?: string | null;
}): Promise<{ content: string }> {
  return fetchJson(
    '/api/recovery/instructions',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
    'operational instructions failed',
  );
}

export async function acknowledgeRecovery(recoveryId: string): Promise<void> {
  await fetchJson(
    `/api/recovery/${encodeURIComponent(recoveryId)}/acknowledge`,
    { method: 'POST' },
    'acknowledge recovery failed',
  );
}

export async function resumeRecoveredRun(runId: string): Promise<void> {
  await fetchJson(
    `/api/recovery/runs/${encodeURIComponent(runId)}/resume`,
    { method: 'POST' },
    'resume recovered run failed',
  );
}

export async function reconcilePlatform(execute = false): Promise<unknown> {
  return fetchJson(
    '/api/platform/reconcile',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ execute }),
    },
    'platform reconcile failed',
  );
}
