import type { LeadPlanRecord } from '../api/lead-plans-api';
import type { WorkspaceTaskRecord, WorkspaceTaskStatus } from '../api/tasks-api';

export type TaskBoardColumnId = 'waiting' | 'in_progress' | 'done' | 'needs_attention';

export type TaskBoardBucket = 'open' | 'leased' | 'done' | 'failed' | 'cancelled';

export type TaskBoardFilter = 'board' | 'history' | 'all';

export type TaskBoardDependencyChip = {
  taskId: string;
  goal: string;
  status: WorkspaceTaskStatus;
  blocking: boolean;
};

export type TaskBoardRow = {
  taskId: string;
  goal: string;
  ownerRole: string;
  status: WorkspaceTaskStatus;
  bucket: TaskBoardBucket;
  column: TaskBoardColumnId;
  meta: string;
  attemptsLabel: string;
  canCancel: boolean;
  canRetry: boolean;
  runId: string | null;
  acceptance: string;
  risk: string;
  attemptBudget: number;
  attemptsUsed: number;
  leaseHolder: string | null;
  leaseExpiresAt: string | null;
  terminalOutcome: string | null;
  allowedPaths: string[];
  exclusivePaths: string[];
  dependencyIds: string[];
  dependencyChips: TaskBoardDependencyChip[];
  blockedByOpenDeps: boolean;
  planId: string | null;
  planKey: string | null;
  planGoal: string | null;
  updatedAt: string;
  createdAt: string;
};

export type TaskBoardPlanGroup = {
  planId: string | null;
  planGoal: string;
  planStatus: string | null;
  awaitingEngagement: boolean;
  rows: TaskBoardRow[];
};

export type OperatorTaskBoardView = {
  purpose: string;
  headline: string;
  emptyCopy: string;
  counts: {
    waiting: number;
    inProgress: number;
    done: number;
    needsAttention: number;
    cancelled: number;
    total: number;
  };
  columns: Array<{
    id: TaskBoardColumnId;
    label: string;
    count: number;
    rows: TaskBoardRow[];
  }>;
  historyRows: TaskBoardRow[];
  planGroups: TaskBoardPlanGroup[];
  rows: TaskBoardRow[];
};

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

export function columnForTask(task: WorkspaceTaskRecord): TaskBoardColumnId | null {
  if (task.status === 'cancelled') {
    return null;
  }
  if (task.status === 'failed') {
    return 'needs_attention';
  }
  if (task.status === 'leased') {
    return 'in_progress';
  }
  if (task.status === 'completed') {
    return 'done';
  }
  // open — blocked dependencies still sit in Waiting with a chip, not a fake drag.
  return 'waiting';
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
  if (task.plan_id) {
    parts.push('Lead plan');
  }
  return parts.join(' · ') || task.status;
}

function sortNewest(left: WorkspaceTaskRecord, right: WorkspaceTaskRecord): number {
  return right.updated_at.localeCompare(left.updated_at);
}

function toRow(
  task: WorkspaceTaskRecord,
  byId: Map<string, WorkspaceTaskRecord>,
  planById: Map<string, LeadPlanRecord>,
): TaskBoardRow {
  const dependencyIds = Array.isArray(task.dependencies) ? task.dependencies : [];
  const dependencyChips: TaskBoardDependencyChip[] = dependencyIds.map((depId) => {
    const dep = byId.get(depId);
    const status = dep?.status ?? 'open';
    return {
      taskId: depId,
      goal: dep?.goal?.trim() || depId.slice(0, 12),
      status,
      blocking: status === 'open' || status === 'leased' || status === 'failed',
    };
  });
  const blockedByOpenDeps = dependencyChips.some((chip) => chip.blocking);
  const planId = task.plan_id?.trim() || null;
  const plan = planId ? planById.get(planId) : undefined;
  const column = columnForTask(task);

  return {
    taskId: task.task_id,
    goal: task.goal,
    ownerRole: task.owner_role.trim() || 'unassigned',
    status: task.status,
    bucket: bucketForStatus(task.status),
    column: column ?? 'needs_attention',
    meta: formatMeta(task),
    attemptsLabel: `${task.attempts_used}/${task.attempt_budget}`,
    canCancel: task.status === 'open' || task.status === 'leased',
    canRetry: task.status === 'failed' || task.status === 'cancelled',
    runId: task.run_id,
    acceptance: task.acceptance_criteria.trim(),
    risk: (task.risk || 'normal').trim() || 'normal',
    attemptBudget: task.attempt_budget,
    attemptsUsed: task.attempts_used,
    leaseHolder: task.lease_holder,
    leaseExpiresAt: task.lease_expires_at,
    terminalOutcome: task.terminal_outcome,
    allowedPaths: task.allowed_paths ?? [],
    exclusivePaths: task.exclusive_paths ?? [],
    dependencyIds,
    dependencyChips,
    blockedByOpenDeps,
    planId,
    planKey: task.plan_key?.trim() || null,
    planGoal: plan?.goal?.trim() || null,
    updatedAt: task.updated_at,
    createdAt: task.created_at,
  };
}

export function filterTaskBoardRows(
  rows: TaskBoardRow[],
  filter: TaskBoardFilter,
): TaskBoardRow[] {
  if (filter === 'all') {
    return rows;
  }
  if (filter === 'history') {
    return rows.filter((row) => row.bucket === 'cancelled' || row.bucket === 'done');
  }
  return rows.filter((row) => row.bucket !== 'cancelled');
}

export function buildOperatorTaskBoardView(
  tasks: WorkspaceTaskRecord[],
  plans: LeadPlanRecord[] = [],
): OperatorTaskBoardView {
  const byId = new Map(tasks.map((task) => [task.task_id, task]));
  const planById = new Map(plans.map((plan) => [plan.plan_id, plan]));
  const planMetaByTaskId = new Map<string, { planId: string; planKey: string }>();
  for (const plan of plans) {
    for (const link of plan.task_links ?? []) {
      if (!link.task_id) {
        continue;
      }
      planMetaByTaskId.set(link.task_id, {
        planId: plan.plan_id,
        planKey: link.plan_key,
      });
    }
  }
  const ordered = [...tasks].sort(sortNewest).map((task) => {
    const meta = planMetaByTaskId.get(task.task_id);
    if (!meta || task.plan_id) {
      return task;
    }
    return {
      ...task,
      plan_id: meta.planId,
      plan_key: meta.planKey,
    };
  });
  const rows = ordered.map((task) => toRow(task, byId, planById));

  const waiting = rows.filter((row) => row.column === 'waiting' && row.bucket !== 'cancelled');
  const inProgress = rows.filter(
    (row) => row.column === 'in_progress' && row.bucket !== 'cancelled',
  );
  const done = rows.filter((row) => row.column === 'done' && row.bucket !== 'cancelled');
  const needsAttention = rows.filter(
    (row) => row.column === 'needs_attention' && row.bucket !== 'cancelled',
  );
  const historyRows = rows.filter((row) => row.bucket === 'cancelled');

  const counts = {
    waiting: waiting.length,
    inProgress: inProgress.length,
    done: done.length,
    needsAttention: needsAttention.length,
    cancelled: historyRows.length,
    total: tasks.length,
  };

  const columns: OperatorTaskBoardView['columns'] = [
    { id: 'waiting', label: 'Waiting', count: counts.waiting, rows: waiting },
    { id: 'in_progress', label: 'In progress', count: counts.inProgress, rows: inProgress },
    { id: 'done', label: 'Done', count: counts.done, rows: done },
    {
      id: 'needs_attention',
      label: 'Needs attention',
      count: counts.needsAttention,
      rows: needsAttention,
    },
  ];

  const planGroups: TaskBoardPlanGroup[] = [];
  const groupedTaskIds = new Set<string>();
  for (const plan of plans) {
    const planRows = rows.filter((row) => row.planId === plan.plan_id && row.bucket !== 'cancelled');
    if (!planRows.length) {
      continue;
    }
    for (const row of planRows) {
      groupedTaskIds.add(row.taskId);
    }
    planGroups.push({
      planId: plan.plan_id,
      planGoal: plan.goal || 'Lead plan',
      planStatus: String(plan.status || ''),
      awaitingEngagement: Boolean(plan.awaiting_engagement),
      rows: planRows,
    });
  }
  const unplanned = rows.filter(
    (row) => !groupedTaskIds.has(row.taskId) && row.bucket !== 'cancelled',
  );
  if (unplanned.length) {
    planGroups.push({
      planId: null,
      planGoal: 'Ungrouped tasks',
      planStatus: null,
      awaitingEngagement: false,
      rows: unplanned,
    });
  }

  const liveCount = counts.waiting + counts.inProgress;
  let headline = 'Nothing queued';
  let purpose = 'Specialist queue by status.';
  let emptyCopy = 'No open work — create a task or Lead fan-out.';

  if (counts.needsAttention > 0) {
    headline = `${counts.needsAttention} need attention · ${liveCount} live`;
    purpose = 'Failed work needs retry before the queue clears.';
    emptyCopy = 'Empty.';
  } else if (liveCount > 0) {
    headline = `${counts.inProgress} in progress · ${counts.waiting} waiting`;
    purpose = 'Dependency chips mark blockers.';
    emptyCopy = 'Empty.';
  } else if (counts.done > 0) {
    headline = `${counts.done} done`;
    purpose = 'No live work.';
    emptyCopy = 'Empty.';
  } else if (counts.cancelled > 0) {
    headline = `${counts.cancelled} cancelled`;
    purpose = 'History only — create new work to assign.';
    emptyCopy = 'Empty.';
  }

  return {
    purpose,
    headline,
    emptyCopy,
    counts,
    columns,
    historyRows,
    planGroups,
    rows,
  };
}
