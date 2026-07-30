import type { CompanyEmployeeRecord, RunRecord } from '../../contracts/canonical';
import type { WorkspaceTaskRecord } from '../../api/tasks-api';
import { normalizeAutonomyMode } from '../../lib/operator-presence-settings';

export type EmployeeManualHandoff = {
  waiting: boolean;
  taskId: string | null;
  reason: 'open_task' | 'assigned' | null;
};

function roleKey(value: string | null | undefined): string {
  return String(value || '')
    .trim()
    .toLowerCase();
}

function taskIsUnblocked(
  task: WorkspaceTaskRecord,
  byId: Map<string, WorkspaceTaskRecord>,
): boolean {
  const deps = Array.isArray(task.dependencies) ? task.dependencies : [];
  return deps.every((depId) => {
    const dep = byId.get(depId);
    const status = dep?.status ?? 'open';
    return status === 'completed' || status === 'cancelled';
  });
}

/**
 * Manual autonomy: handoffs wait for an explicit Start. Semi/Full hide Start Now
 * (Full auto-leases; Semi still uses Mission Control START / Lead Send).
 */
export function resolveEmployeeManualHandoff(input: {
  employee: CompanyEmployeeRecord;
  autonomyMode: string | null | undefined;
  tasks: readonly WorkspaceTaskRecord[];
  runs?: readonly Pick<RunRecord, 'run_id' | 'task_id'>[];
}): EmployeeManualHandoff {
  if (normalizeAutonomyMode(input.autonomyMode) !== 'manual') {
    return { waiting: false, taskId: null, reason: null };
  }
  if (!input.employee.enabled) {
    return { waiting: false, taskId: null, reason: null };
  }

  const role = roleKey(input.employee.role);
  if (!role) {
    return { waiting: false, taskId: null, reason: null };
  }

  const byId = new Map(input.tasks.map((task) => [task.task_id, task]));
  const status = roleKey(input.employee.status);
  const activeRunId = input.employee.active_run_id?.trim() ?? '';
  const activeRunTaskId =
    input.runs?.find((run) => run.run_id.trim() === activeRunId)?.task_id?.trim() ?? '';
  const assignedTask =
    input.tasks.find(
      (task) =>
        roleKey(task.owner_role) === role &&
        task.status === 'leased' &&
        ((activeRunId && task.run_id?.trim() === activeRunId) ||
          (activeRunTaskId && task.task_id === activeRunTaskId)),
    ) ?? null;

  // An assigned employee's bound run is authoritative. Never let an unrelated
  // newer open task steal this Start button.
  if (status === 'assigned' && (assignedTask || activeRunTaskId)) {
    return {
      waiting: true,
      taskId: assignedTask?.task_id ?? activeRunTaskId,
      reason: 'assigned',
    };
  }
  if (['executing', 'working', 'running', 'starting', 'planning'].includes(status)) {
    return { waiting: false, taskId: null, reason: null };
  }

  const openTask = [...input.tasks]
    .filter(
      (task) =>
        roleKey(task.owner_role) === role &&
        task.status === 'open' &&
        taskIsUnblocked(task, byId),
    )
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at))[0];

  if (openTask) {
    return { waiting: true, taskId: openTask.task_id, reason: 'open_task' };
  }

  const leasedQueued = [...input.tasks]
    .filter(
      (task) =>
        roleKey(task.owner_role) === role &&
        task.status === 'leased' &&
        Boolean(task.run_id?.trim()),
    )
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at))[0];

  if (leasedQueued && status === 'assigned') {
    return { waiting: true, taskId: leasedQueued.task_id, reason: 'assigned' };
  }

  // Do not show a handoff glow that has no actionable task behind it.
  return { waiting: false, taskId: null, reason: null };
}
