import type {
  InboxItem,
  OperatorBriefing,
  RunRecord,
  RuntimeSummary,
  WorkspaceRecord,
} from '../contracts/canonical';

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

export async function fetchInbox(): Promise<InboxSnapshot> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/inbox` : '/api/inbox';
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`inbox request failed with status ${response.status}`);
  }

  return response.json() as Promise<InboxSnapshot>;
}

export async function fetchOperatorBriefing(): Promise<OperatorBriefing> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/briefing` : '/api/briefing';
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`operator briefing request failed with status ${response.status}`);
  }

  return response.json() as Promise<OperatorBriefing>;
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

export async function fetchWorkspaces(): Promise<WorkspaceListSnapshot> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/workspaces` : '/api/workspaces';
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
