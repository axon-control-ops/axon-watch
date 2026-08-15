import type { WorkspaceTaskRecord } from '../api/tasks-api';

export type TaskDependencyBlocker = {
  taskId: string;
  status: string;
  ownerRole: string;
  summary: string;
};

export function taskDependencyBlockers(
  task: WorkspaceTaskRecord,
  byId: Map<string, WorkspaceTaskRecord>,
): TaskDependencyBlocker[] {
  const deps = Array.isArray(task.dependencies) ? task.dependencies : [];
  const blockers: TaskDependencyBlocker[] = [];
  for (const depId of deps) {
    const cleaned = String(depId || '').trim();
    if (!cleaned) {
      continue;
    }
    const dep = byId.get(cleaned);
    if (!dep) {
      blockers.push({
        taskId: cleaned,
        status: 'missing',
        ownerRole: '',
        summary: 'missing dependency',
      });
      continue;
    }
    const status = String(dep.status || 'open').trim().toLowerCase();
    if (status !== 'completed') {
      blockers.push({
        taskId: cleaned,
        status,
        ownerRole: String(dep.owner_role || '')
          .trim()
          .toLowerCase(),
        summary: String(dep.goal || cleaned).slice(0, 120),
      });
    }
  }
  return blockers;
}

/** Matches control-plane `dependencies_completed` — only `completed` satisfies a dep. */
export function taskDependenciesCompleted(
  task: WorkspaceTaskRecord,
  byId: Map<string, WorkspaceTaskRecord>,
): boolean {
  return taskDependencyBlockers(task, byId).length === 0;
}

export function taskDependencyBlockerMessage(
  task: WorkspaceTaskRecord,
  byId: Map<string, WorkspaceTaskRecord>,
): string {
  const blockers = taskDependencyBlockers(task, byId);
  if (!blockers.length) {
    return '';
  }
  const parts = blockers.slice(0, 3).map((row) => {
    const role = row.ownerRole || 'task';
    return `${role} ${row.taskId} (${row.status})`;
  });
  const suffix = blockers.length > 3 ? ` (+${blockers.length - 3} more)` : '';
  return `blocked by unfinished dependencies: ${parts.join(', ')}${suffix}`;
}

export function humanizeHandoffBlockedReason(
  task: WorkspaceTaskRecord,
  byId: Map<string, WorkspaceTaskRecord>,
): string {
  const blockers = taskDependencyBlockers(task, byId);
  if (!blockers.length) {
    return '';
  }
  const first = blockers[0];
  const roleLabel = first.ownerRole || 'teammate';
  if (first.summary.toLowerCase().startsWith('verification after')) {
    return `Waiting on ${roleLabel} verification before this handoff can start.`;
  }
  return `Waiting on ${roleLabel} (${first.status}) before Start now is available.`;
}
