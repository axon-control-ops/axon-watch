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
  exclusive_paths?: string[];
  allowed_paths?: string[];
  status: WorkspaceTaskStatus;
  lease_holder: string | null;
  lease_expires_at: string | null;
  attempt_budget: number;
  attempts_used: number;
  terminal_outcome: string | null;
  run_id: string | null;
  created_at: string;
  updated_at: string;
  /** Populated client-side from Lead plan mappings when available. */
  plan_id?: string | null;
  plan_key?: string | null;
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
  exclusive_paths?: string[];
  allowed_paths?: string[];
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

export type OperatorStartTaskResult = {
  task: WorkspaceTaskRecord;
  run: { run_id?: string; [key: string]: unknown };
  thread_id: string | null;
};

export async function operatorStartWorkspaceTask(
  taskId: string,
): Promise<OperatorStartTaskResult> {
  const encoded = encodeURIComponent(taskId);
  return fetchJson<OperatorStartTaskResult>(
    `/api/tasks/${encoded}/operator-start`,
    { method: 'POST' },
    'operator start task failed',
  );
}

export type CancelWorkspaceTasksBatchResult = {
  workspace_id: string;
  cancelled_count: number;
  cancelled: WorkspaceTaskRecord[];
  errors: Array<{ task_id: string; detail: string }>;
};

export async function cancelWorkspaceTasksBatch(
  workspaceId: string,
  input: { taskIds?: string[]; scope?: 'waiting' | ''; terminalOutcome?: string } = {},
): Promise<CancelWorkspaceTasksBatchResult> {
  const encoded = encodeURIComponent(workspaceId);
  return fetchJson<CancelWorkspaceTasksBatchResult>(
    `/api/workspaces/${encoded}/tasks/cancel-batch`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        task_ids: input.taskIds ?? [],
        scope: input.scope ?? '',
        terminal_outcome: input.terminalOutcome ?? 'cancelled by operator',
      }),
    },
    'cancel workspace tasks batch failed',
  );
}
