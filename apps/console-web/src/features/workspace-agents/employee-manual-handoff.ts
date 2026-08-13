import type { CompanyEmployeeRecord, RunRecord } from '../../contracts/canonical';
import type { WorkspaceTaskRecord } from '../../api/tasks-api';
import { normalizeAutonomyMode } from '../../lib/operator-presence-settings';
import {
  humanizeHandoffBlockedReason,
  taskDependenciesCompleted,
} from '../../lib/task-dependencies';

import { employeeIsActivelyBusy } from './company-roster-busy';

export type EmployeeManualHandoff = {
  waiting: boolean;
  taskId: string | null;
  reason: 'open_task' | 'assigned' | null;
  /** Set when a handoff ticket exists but unfinished deps block Operator Start. */
  blockedReason: string | null;
};

function roleKey(value: string | null | undefined): string {
  return String(value || '')
    .trim()
    .toLowerCase();
}

/** A task with an exhausted attempt budget cannot be leased by Operator Start. */
function taskHasAttemptCapacity(task: WorkspaceTaskRecord): boolean {
  return task.attempts_used < task.attempt_budget;
}

/** Matches control-plane cross-workspace handoff acceptance prefix. */
export function taskLooksLikeCrossWorkspaceHandoff(task: WorkspaceTaskRecord): boolean {
  const acceptance = String(task.acceptance_criteria || '')
    .trim()
    .toLowerCase();
  return acceptance.includes('cross-workspace handoff');
}

/**
 * Semi only offers Start now for Lead board tickets and cross-workspace handoffs
 * (capacity / busy soft-fails). Manual keeps Start for any open role handoff.
 */
export function taskIsSemiStartFallback(task: WorkspaceTaskRecord): boolean {
  if (roleKey(task.owner_role) === 'lead') {
    return true;
  }
  return taskLooksLikeCrossWorkspaceHandoff(task);
}

const IN_FLIGHT_STATUSES = new Set([
  'executing',
  'working',
  'running',
  'starting',
  'planning',
  'verifying',
]);

/**
 * Manual: handoffs wait for an explicit Start.
 * Semi: auto-start runs on the control plane; Start now is a fallback when a
 * Lead / cross-workspace ticket is still open or leased+queued.
 * Full: continuous leasing owns starts — hide Start now.
 *
 * Start now only when there is a real handoff wait and the teammate is not busy
 * (roster mid-shift or live IDE stream). Busy + no handoff both hide the button.
 */
export function resolveEmployeeManualHandoff(input: {
  employee: CompanyEmployeeRecord;
  autonomyMode: string | null | undefined;
  tasks: readonly WorkspaceTaskRecord[];
  runs?: readonly Pick<RunRecord, 'run_id' | 'task_id'>[];
  /** True when this teammate owns an active IDE stream (Team BUSY badge). */
  liveBusy?: boolean;
}): EmployeeManualHandoff {
  const idle = {
    waiting: false,
    taskId: null,
    reason: null,
    blockedReason: null,
  } satisfies EmployeeManualHandoff;
  const mode = normalizeAutonomyMode(input.autonomyMode);
  if (mode === 'full' || (mode !== 'manual' && mode !== 'semi')) {
    return idle;
  }
  if (!input.employee.enabled) {
    return idle;
  }

  const role = roleKey(input.employee.role);
  if (!role) {
    return idle;
  }

  const status = roleKey(input.employee.status);
  // Never offer Start now while a run is already in flight or the IDE is streaming.
  if (
    input.liveBusy ||
    employeeIsActivelyBusy(input.employee) ||
    IN_FLIGHT_STATUSES.has(status)
  ) {
    return idle;
  }

  const byId = new Map(input.tasks.map((task) => [task.task_id, task]));
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

  const allowsTask = (task: WorkspaceTaskRecord): boolean =>
    mode === 'manual' || taskIsSemiStartFallback(task);

  const blockedReasonFor = (task: WorkspaceTaskRecord): string | null => {
    if (taskDependenciesCompleted(task, byId)) {
      return null;
    }
    return humanizeHandoffBlockedReason(task, byId);
  };

  // An assigned employee's bound run is authoritative. Never let an unrelated
  // newer open task steal this Start button.
  if (status === 'assigned' && (assignedTask || activeRunTaskId)) {
    if (assignedTask && !allowsTask(assignedTask)) {
      return idle;
    }
    const boundTask =
      assignedTask ??
      (activeRunTaskId ? byId.get(activeRunTaskId) ?? null : null);
    if (boundTask) {
      const blockedReason = blockedReasonFor(boundTask);
      if (blockedReason) {
        return { ...idle, blockedReason };
      }
    }
    return {
      waiting: true,
      taskId: assignedTask?.task_id ?? activeRunTaskId,
      reason: 'assigned',
      blockedReason: null,
    };
  }

  const openCandidates = [...input.tasks]
    .filter(
      (task) =>
        roleKey(task.owner_role) === role &&
        task.status === 'open' &&
        taskHasAttemptCapacity(task) &&
        allowsTask(task),
    )
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at));

  const openTask =
    openCandidates.find((task) => taskDependenciesCompleted(task, byId)) ?? null;
  const blockedOpenTask =
    openCandidates.find((task) => !taskDependenciesCompleted(task, byId)) ?? null;

  if (openTask) {
    return {
      waiting: true,
      taskId: openTask.task_id,
      reason: 'open_task',
      blockedReason: null,
    };
  }

  const leasedQueued = [...input.tasks]
    .filter(
      (task) =>
        roleKey(task.owner_role) === role &&
        task.status === 'leased' &&
        Boolean(task.run_id?.trim()) &&
        allowsTask(task),
    )
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at))[0];

  if (leasedQueued && status === 'assigned') {
    const blockedReason = blockedReasonFor(leasedQueued);
    if (blockedReason) {
      return { ...idle, blockedReason };
    }
    return {
      waiting: true,
      taskId: leasedQueued.task_id,
      reason: 'assigned',
      blockedReason: null,
    };
  }

  if (blockedOpenTask) {
    return {
      ...idle,
      blockedReason: blockedReasonFor(blockedOpenTask),
    };
  }

  // Do not show a handoff glow that has no actionable task behind it.
  return idle;
}
