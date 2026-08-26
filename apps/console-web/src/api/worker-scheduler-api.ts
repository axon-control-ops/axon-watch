import type { CompanyRosterSnapshot } from '../contracts/canonical';

import { fetchJson } from './client';

export interface WorkerSchedulerStatus {
  watcher_scheduler_enabled: boolean;
  watcher_effective_enabled: boolean;
  watcher_env_allowed: boolean;
  watcher_blocked_by_env: boolean;
  scheduler_enabled: boolean;
  effective_enabled: boolean;
  env_allowed: boolean;
  blocked_by_env: boolean;
  max_active: number;
  max_starts_per_tick: number;
  tick_interval_seconds: number;
  dispatch_enabled: boolean;
  executing_count: number;
  active_run_count: number;
  employee_enabled: Record<string, boolean>;
  updated_at?: string | null;
  stopped_run_ids?: string[];
  stop_errors?: Array<{ run_id: string; error: string }>;
  /** Idle ticks never invoke Cursor CLI; only dispatched shifts bill usage. */
  cursor_usage_on_idle_tick?: boolean;
  cursor_usage_policy?: 'dispatch_only' | string;
  hard_killed?: boolean;
  resumed?: boolean;
}

export interface WorkerSchedulerPatch {
  watcher_scheduler_enabled?: boolean;
  scheduler_enabled?: boolean;
  max_active?: number;
  max_starts_per_tick?: number;
}

export type EmployeeEnabledPatchResponse = CompanyRosterSnapshot & {
  workspace_id: string;
  role: string;
  enabled: boolean;
  key: string;
};

export type EmployeeClearRunCardResponse = CompanyRosterSnapshot & {
  workspace_id: string;
  role: string;
  dismissed_run_ids: string[];
  dismissed_count: number;
  reconciled_missing_task_run_ids: string[];
};

export function fetchWorkerSchedulerStatus(): Promise<WorkerSchedulerStatus> {
  return fetchJson<WorkerSchedulerStatus>(
    '/api/worker-scheduler',
    {},
    'worker scheduler request failed',
  );
}

export function patchWorkerScheduler(
  patch: WorkerSchedulerPatch,
): Promise<WorkerSchedulerStatus> {
  return fetchJson<WorkerSchedulerStatus>(
    '/api/worker-scheduler',
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    },
    'worker scheduler patch failed',
  );
}

export function stopActiveWorkerRuns(): Promise<WorkerSchedulerStatus> {
  return fetchJson<WorkerSchedulerStatus>(
    '/api/worker-scheduler/stop-active',
    { method: 'POST' },
    'stop active workers request failed',
  );
}

export function hardKillWorkerScheduler(): Promise<WorkerSchedulerStatus> {
  return fetchJson<WorkerSchedulerStatus>(
    '/api/worker-scheduler/hard-kill',
    { method: 'POST' },
    'hard-kill worker scheduler request failed',
  );
}

export function resumeWorkerScheduler(): Promise<WorkerSchedulerStatus> {
  return fetchJson<WorkerSchedulerStatus>(
    '/api/worker-scheduler/resume',
    { method: 'POST' },
    'resume worker scheduler request failed',
  );
}

export function patchWorkspaceEmployeeEnabled(
  workspaceId: string,
  employeeId: string,
  enabled: boolean,
): Promise<EmployeeEnabledPatchResponse> {
  const encodedWorkspace = encodeURIComponent(workspaceId);
  const encodedEmployee = encodeURIComponent(employeeId);
  return fetchJson<EmployeeEnabledPatchResponse>(
    `/api/workspaces/${encodedWorkspace}/company/employees/${encodedEmployee}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled }),
    },
    'employee enabled patch failed',
  );
}

export function clearWorkspaceEmployeeRunCard(
  workspaceId: string,
  employeeId: string,
): Promise<EmployeeClearRunCardResponse> {
  const encodedWorkspace = encodeURIComponent(workspaceId);
  const encodedEmployee = encodeURIComponent(employeeId);
  return fetchJson<EmployeeClearRunCardResponse>(
    `/api/workspaces/${encodedWorkspace}/company/employees/${encodedEmployee}/clear-run-card`,
    { method: 'POST' },
    'clear agent run card failed',
  );
}
