import type { WorkspaceTaskRecord, WorkspaceTaskStatus } from '../api/tasks-api';

export type TaskBoardBucket = 'open' | 'leased' | 'done' | 'failed' | 'cancelled';

export type TaskBoardFilter = 'active' | 'done' | 'failed' | 'cancelled' | 'all';

export type TaskBoardRow = {
  taskId: string;
  goal: string;
  ownerRole: string;
  status: WorkspaceTaskStatus;
  bucket: TaskBoardBucket;
  meta: string;
  attemptsLabel: string;
  canCancel: boolean;
  runId: string | null;
  acceptance: string;
  updatedAt: string;
};

export type OperatorTaskBoardView = {
  /** One plain sentence: what this board is for right now. */
  purpose: string;
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
  /** Default filter when the operator opens the board. */
  defaultFilter: TaskBoardFilter;
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
  if (status === 'cancelled') {
    return 'cancelled';
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
    parts.push(task.run_id.slice(0, 18));
  }
  return parts.join(' · ') || task.status;
}

function toRow(task: WorkspaceTaskRecord): TaskBoardRow {
  return {
    taskId: task.task_id,
    goal: task.goal,
    ownerRole: task.owner_role.trim() || 'unassigned',
    status: task.status,
    bucket: bucketForStatus(task.status),
    meta: formatMeta(task),
    attemptsLabel: `${task.attempts_used}/${task.attempt_budget}`,
    canCancel: task.status === 'open' || task.status === 'leased',
    runId: task.run_id,
    acceptance: task.acceptance_criteria.trim(),
    updatedAt: task.updated_at,
  };
}

function sortNewest(left: WorkspaceTaskRecord, right: WorkspaceTaskRecord): number {
  return right.updated_at.localeCompare(left.updated_at);
}

export function filterTaskBoardRows(
  rows: TaskBoardRow[],
  filter: TaskBoardFilter,
): TaskBoardRow[] {
  if (filter === 'all') {
    return rows;
  }
  if (filter === 'active') {
    return rows.filter((row) => row.bucket === 'open' || row.bucket === 'leased');
  }
  if (filter === 'done') {
    return rows.filter((row) => row.bucket === 'done');
  }
  if (filter === 'failed') {
    return rows.filter((row) => row.bucket === 'failed');
  }
  return rows.filter((row) => row.bucket === 'cancelled');
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
      return sortNewest(left, right);
    });
  const completed = tasks
    .filter((task) => task.status === 'completed')
    .sort(sortNewest);
  const failed = tasks.filter((task) => task.status === 'failed').sort(sortNewest);
  const cancelled = tasks
    .filter((task) => task.status === 'cancelled')
    .sort(sortNewest);

  // Prefer real outcomes over cancelled noise in the default list ordering.
  const ordered = [...active, ...failed, ...completed, ...cancelled];
  const rows = ordered.map(toRow);

  const activeCount = counts.open + counts.leased;
  let defaultFilter: TaskBoardFilter = 'active';
  let headline = 'Nothing queued';
  let purpose =
    'Specialist work queue: create a goal, a role leases it, then it lands done or failed.';
  let emptyCopy = 'No open or leased work. Create a task below, or check Done / Failed.';

  if (activeCount > 0) {
    headline = `${counts.leased} leased · ${counts.open} waiting`;
    purpose = 'Live work for continuous workers — leased is in progress, open is waiting.';
    emptyCopy = 'No active tasks in this filter.';
  } else if (counts.failed > 0) {
    defaultFilter = 'failed';
    headline = `${counts.failed} failed · ${counts.completed} done`;
    purpose = 'No live work. Failed items need a new task or a fix before retrying.';
    emptyCopy = 'No failed tasks.';
  } else if (counts.completed > 0) {
    defaultFilter = 'done';
    headline = `${counts.completed} done`;
    purpose = 'No live work. Done = finished successfully. Cancelled history is under Cancelled.';
    emptyCopy = 'No completed tasks.';
  } else if (counts.cancelled > 0) {
    defaultFilter = 'cancelled';
    headline = `${counts.cancelled} cancelled only`;
    purpose =
      'Only cancelled history left — not work. Create a new open task to assign a specialist.';
    emptyCopy = 'No cancelled tasks.';
  }

  return {
    purpose,
    headline,
    emptyCopy,
    counts,
    defaultFilter,
    rows,
  };
}
