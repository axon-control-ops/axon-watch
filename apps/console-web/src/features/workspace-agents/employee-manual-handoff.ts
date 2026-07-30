import type { CompanyEmployeeRecord } from '../../contracts/canonical';
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
}): EmployeeManualHandoff {
  if (normalizeAutonomyMode(input.autonomyMode) !== 'manual') {
    return { waiting: false, taskId: null, reason: null };
  }
  if (!input.employee.enabled) {
    return { waiting: false, taskId: null, reason: null };
  }

  const role = roleKey(input.employee.role);
  if (!role || role === 'lead') {
    // Lead rarely owns Waiting START tickets; glow stays on specialists.
    const status = roleKey(input.employee.status);
    if (status === 'assigned') {
      return { waiting: true, taskId: null, reason: 'assigned' };
    }
    return { waiting: false, taskId: null, reason: null };
  }

  const byId = new Map(input.tasks.map((task) => [task.task_id, task]));
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

  if (leasedQueued && roleKey(input.employee.status) === 'assigned') {
    return { waiting: true, taskId: leasedQueued.task_id, reason: 'assigned' };
  }

  if (roleKey(input.employee.status) === 'assigned') {
    return {
      waiting: true,
      taskId: leasedQueued?.task_id ?? null,
      reason: 'assigned',
    };
  }

  return { waiting: false, taskId: null, reason: null };
}
