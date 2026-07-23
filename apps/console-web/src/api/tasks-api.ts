import { fetchJson } from './client';

export type WorkspaceTaskStatus =
  | 'open'
  | 'leased'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type WorkspaceTaskRecord = {
  task_id: string;
  workspace_id: string;
  goal: string;
  acceptance_criteria: string;
  risk: string;
  owner_role: string;
  dependencies: string[];
  status: WorkspaceTaskStatus;
  lease_holder: string | null;
  lease_expires_at: string | null;
  attempt_budget: number;
  attempts_used: number;
  terminal_outcome: string | null;
  run_id: string | null;
  created_at: string;
  updated_at: string;
};

export type WorkspaceTasksSnapshot = {
  workspace_id: string;
  items: WorkspaceTaskRecord[];
};

export type CreateWorkspaceTaskInput = {
  goal: string;
  acceptance_criteria?: string;
  risk?: string;
  owner_role?: string;
  dependencies?: string[];
  attempt_budget?: number;
};

export async function fetchWorkspaceTasks(
  workspaceId: string,
  options: { status?: string; ownerRole?: string; limit?: number } = {},
): Promise<WorkspaceTasksSnapshot> {
  const encoded = encodeURIComponent(workspaceId);
  const params = new URLSearchParams();
  if (options.status) {
    params.set('status', options.status);
  }
  if (options.ownerRole) {
    params.set('owner_role', options.ownerRole);
  }
  if (options.limit != null) {
    params.set('limit', String(options.limit));
  }
  const query = params.toString();
  const suffix = query ? `?${query}` : '';
  return fetchJson<WorkspaceTasksSnapshot>(
    `/api/workspaces/${encoded}/tasks${suffix}`,
    {},
    'workspace tasks request failed',
  );
}

export async function createWorkspaceTask(
  workspaceId: string,
  input: CreateWorkspaceTaskInput,
): Promise<WorkspaceTaskRecord> {
  const encoded = encodeURIComponent(workspaceId);
  return fetchJson<WorkspaceTaskRecord>(
    `/api/workspaces/${encoded}/tasks`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    },
    'create workspace task failed',
  );
}

export async function cancelWorkspaceTask(
  taskId: string,
  terminalOutcome = 'cancelled',
): Promise<WorkspaceTaskRecord> {
  const encoded = encodeURIComponent(taskId);
  return fetchJson<WorkspaceTaskRecord>(
    `/api/tasks/${encoded}/cancel`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ terminal_outcome: terminalOutcome }),
    },
    'cancel workspace task failed',
  );
}
