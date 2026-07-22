import type { WorkspaceTaskRecord, WorkspaceTaskStatus } from '../api/tasks-api';

export type TaskBoardBucket = 'open' | 'leased' | 'done' | 'failed';

export type TaskBoardRow = {
  taskId: string;
  goal: string;
  ownerRole: string;
  status: WorkspaceTaskStatus;
  bucket: TaskBoardBucket;
  meta: string;
  attemptsLabel: string;
  canCancel: boolean;
};

export type OperatorTaskBoardView = {
  headline: string;
  emptyCopy: string;
  counts: {
    open: number;
    leased: number;
    completed: number;
    failed: number;
    cancelled: number;
    total: number;
  };
  rows: TaskBoardRow[];
};

const ACTIVE_STATUSES = new Set<WorkspaceTaskStatus>(['open', 'leased']);

function bucketForStatus(status: WorkspaceTaskStatus): TaskBoardBucket {
  if (status === 'open') {
    return 'open';
  }
  if (status === 'leased') {
    return 'leased';
  }
  if (status === 'failed') {
    return 'failed';
  }
  return 'done';
}

function formatMeta(task: WorkspaceTaskRecord): string {
  const parts: string[] = [];
  const role = task.owner_role.trim();
  if (role) {
    parts.push(role);
  }
  if (task.status === 'leased' && task.lease_holder) {
    parts.push(`held by ${task.lease_holder}`);
  }
  if (task.run_id) {
    parts.push(task.run_id);
  }
  if (task.terminal_outcome && !ACTIVE_STATUSES.has(task.status)) {
    parts.push(task.terminal_outcome);
  }
  return parts.join(' · ') || task.status;
}

export function buildOperatorTaskBoardView(
  tasks: WorkspaceTaskRecord[],
): OperatorTaskBoardView {
  const counts = {
    open: 0,
    leased: 0,
    completed: 0,
    failed: 0,
    cancelled: 0,
    total: tasks.length,
  };
  for (const task of tasks) {
    if (task.status === 'open') {
      counts.open += 1;
    } else if (task.status === 'leased') {
      counts.leased += 1;
    } else if (task.status === 'completed') {
      counts.completed += 1;
    } else if (task.status === 'failed') {
      counts.failed += 1;
    } else if (task.status === 'cancelled') {
      counts.cancelled += 1;
    }
  }

  const active = tasks
    .filter((task) => ACTIVE_STATUSES.has(task.status))
    .sort((left, right) => {
      if (left.status !== right.status) {
        return left.status === 'leased' ? -1 : 1;
      }
      return right.updated_at.localeCompare(left.updated_at);
    });

  const recentTerminal = tasks
    .filter((task) => !ACTIVE_STATUSES.has(task.status))
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at))
    .slice(0, 4);

  const rows: TaskBoardRow[] = [...active, ...recentTerminal].map((task) => ({
    taskId: task.task_id,
    goal: task.goal,
    ownerRole: task.owner_role.trim() || 'unassigned',
    status: task.status,
    bucket: bucketForStatus(task.status),
    meta: formatMeta(task),
    attemptsLabel: `${task.attempts_used}/${task.attempt_budget}`,
    canCancel: task.status === 'open',
  }));

  const activeCount = counts.open + counts.leased;
  let headline = 'No leased work';
  if (activeCount > 0) {
    headline = `${counts.leased} leased · ${counts.open} open`;
  } else if (counts.completed > 0 || counts.failed > 0) {
    headline = `${counts.completed} done · ${counts.failed} failed`;
  }

  return {
    headline,
    emptyCopy: 'No tasks yet — seed an open goal for a specialist role.',
    counts,
    rows,
  };
}
