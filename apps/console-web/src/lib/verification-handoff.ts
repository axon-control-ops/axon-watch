import type { CompanyEmployeeRecord, RunRecord } from '../contracts/canonical';
import type { WorkspaceTaskRecord } from '../api/tasks-api';
import { isGate6AcceptanceFailure } from '../features/workspace-agents/employee-failure-detail';

/** Matches control-plane verification handoff goal prefix. */
export function taskIsVerificationHandoff(task: WorkspaceTaskRecord | null | undefined): boolean {
  return String(task?.goal || '')
    .trim()
    .toLowerCase()
    .startsWith('verification after');
}

/** Operator-facing label for verification vs generic manual start. */
export function verificationHandoffActionLabel(task: WorkspaceTaskRecord | null | undefined): string {
  return taskIsVerificationHandoff(task) ? 'Run verification' : 'Start now';
}

const SPECIALIST_ROLES = new Set(['backend', 'frontend', 'integrations']);

function roleKey(value: string | null | undefined): string {
  return String(value || '')
    .trim()
    .toLowerCase();
}

/** Latest open/leased verification ticket owned by this teammate's role. */
export function findEmployeeVerificationHandoffTask(
  employee: CompanyEmployeeRecord,
  tasks: readonly WorkspaceTaskRecord[],
): WorkspaceTaskRecord | null {
  const role = roleKey(employee.role);
  if (!role) {
    return null;
  }
  return (
    [...tasks]
      .filter(
        (task) =>
          roleKey(task.owner_role) === role &&
          taskIsVerificationHandoff(task) &&
          (task.status === 'open' || task.status === 'leased') &&
          task.attempts_used < task.attempt_budget,
      )
      .sort((left, right) => right.updated_at.localeCompare(left.updated_at))[0] ?? null
  );
}

function taskIdFromEmployeeRuns(
  employee: CompanyEmployeeRecord,
  runs: readonly Pick<RunRecord, 'run_id' | 'task_id'>[] | undefined,
): string | null {
  const candidates = [
    employee.active_run_id?.trim(),
    employee.last_run_id?.trim(),
  ].filter(Boolean) as string[];
  for (const runId of candidates) {
    const taskId = runs?.find((run) => run.run_id.trim() === runId)?.task_id?.trim();
    if (taskId) {
      return taskId;
    }
  }
  return null;
}

/** True when a failed specialist shift looks like a verification/Gate 6 retry. */
export function employeeLooksLikeVerificationRetry(
  employee: CompanyEmployeeRecord,
  tasks: readonly WorkspaceTaskRecord[],
  runs?: readonly Pick<RunRecord, 'run_id' | 'task_id'>[],
): boolean {
  if (findEmployeeVerificationHandoffTask(employee, tasks)) {
    return true;
  }
  const role = roleKey(employee.role);
  if (!SPECIALIST_ROLES.has(role)) {
    return false;
  }
  const outcome = String(employee.last_outcome || '').trim().toLowerCase();
  if (outcome === 'failed' && isGate6AcceptanceFailure(employee.last_outcome_detail)) {
    return true;
  }
  if (outcome !== 'failed') {
    return false;
  }
  const taskId = taskIdFromEmployeeRuns(employee, runs);
  if (!taskId) {
    return false;
  }
  const bound = tasks.find((task) => task.task_id === taskId) ?? null;
  return !bound || taskIsVerificationHandoff(bound) || isGate6AcceptanceFailure(employee.last_outcome_detail);
}

/** Label for the operator-start control on the Team agent card. */
export function operatorStartActionLabel(input: {
  employee: CompanyEmployeeRecord;
  task: WorkspaceTaskRecord | null | undefined;
  tasks: readonly WorkspaceTaskRecord[];
  runs?: readonly Pick<RunRecord, 'run_id' | 'task_id'>[];
}): string {
  if (taskIsVerificationHandoff(input.task)) {
    return 'Run verification';
  }
  if (employeeLooksLikeVerificationRetry(input.employee, input.tasks, input.runs)) {
    return 'Run verification';
  }
  return 'Start now';
}

function taskExistsInLedger(
  taskId: string | null | undefined,
  tasks: readonly WorkspaceTaskRecord[],
): boolean {
  const cleaned = taskId?.trim();
  return Boolean(cleaned && tasks.some((row) => row.task_id === cleaned));
}

/** Prefer ledger rows; allow stale run ids only when no live verification ticket exists. */
function resolveOperatorStartTaskId(input: {
  verificationTask: WorkspaceTaskRecord | null;
  runTaskId: string | null;
  handoffTaskId: string | null;
  handoffTask: WorkspaceTaskRecord | null;
  looksLikeVerify: boolean;
  tasks: readonly WorkspaceTaskRecord[];
}): string | null {
  if (input.verificationTask?.task_id) {
    return input.verificationTask.task_id;
  }
  if (
    input.looksLikeVerify &&
    input.runTaskId &&
    taskExistsInLedger(input.runTaskId, input.tasks)
  ) {
    return input.runTaskId;
  }
  if (
    input.handoffTaskId &&
    taskExistsInLedger(input.handoffTaskId, input.tasks) &&
    (!input.looksLikeVerify || taskIsVerificationHandoff(input.handoffTask))
  ) {
    return input.handoffTaskId;
  }
  if (input.looksLikeVerify && input.runTaskId) {
    return input.runTaskId;
  }
  return null;
}

/**
 * Resolve operator Start / Run verification for the Team card.
 * Prefers verification tickets, then manual handoffs, then failed-run task ids.
 */
export function resolveOperatorStartAction(input: {
  employee: CompanyEmployeeRecord;
  tasks: readonly WorkspaceTaskRecord[];
  runs?: readonly Pick<RunRecord, 'run_id' | 'task_id'>[];
  handoffTaskId?: string | null;
  liveBusy?: boolean;
}): { taskId: string; label: string; task: WorkspaceTaskRecord | null } | null {
  if (input.liveBusy) {
    return null;
  }

  const verificationTask = findEmployeeVerificationHandoffTask(input.employee, input.tasks);
  const runTaskId = taskIdFromEmployeeRuns(input.employee, input.runs);
  const handoffTaskId = input.handoffTaskId?.trim() || null;
  const looksLikeVerify = employeeLooksLikeVerificationRetry(
    input.employee,
    input.tasks,
    input.runs,
  );

  const handoffTask = handoffTaskId
    ? input.tasks.find((row) => row.task_id === handoffTaskId) ?? null
    : null;

  // Gate 6 / verification retries must win over stale implementation handoffs.
  const taskId = resolveOperatorStartTaskId({
    verificationTask,
    runTaskId,
    handoffTaskId,
    handoffTask,
    looksLikeVerify,
    tasks: input.tasks,
  });

  if (!taskId) {
    return null;
  }

  const task =
    input.tasks.find((row) => row.task_id === taskId) ??
    (verificationTask?.task_id === taskId ? verificationTask : null);

  return {
    taskId,
    task,
    label: operatorStartActionLabel({
      employee: input.employee,
      task,
      tasks: input.tasks,
      runs: input.runs,
    }),
  };
}
