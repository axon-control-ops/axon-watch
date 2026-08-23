import type { CompanyEmployeeRecord, RunRecord } from '../../contracts/canonical';
import type { WorkspaceTaskRecord } from '../../api/tasks-api';

import { taskIsVerificationHandoff } from '../../lib/verification-handoff';

const IN_FLIGHT_PHASES = new Set(['executing', 'starting', 'planning', 'queued']);

function activeRunForEmployee(
  employee: CompanyEmployeeRecord,
  runs: readonly Pick<RunRecord, 'run_id' | 'task_id' | 'phase'>[] | undefined,
): Pick<RunRecord, 'run_id' | 'task_id' | 'phase'> | null {
  const runId = employee.active_run_id?.trim();
  if (!runId || !runs?.length) {
    return null;
  }
  return runs.find((run) => run.run_id.trim() === runId) ?? null;
}

/** Short hint for the agent dock while a headless shift is in flight. */
export function employeeRuntimeShiftHint(input: {
  employee: CompanyEmployeeRecord;
  runs?: readonly Pick<RunRecord, 'run_id' | 'task_id' | 'phase'>[];
  tasks?: readonly WorkspaceTaskRecord[];
}): string | null {
  const run = activeRunForEmployee(input.employee, input.runs);
  const phase = String(run?.phase || input.employee.status || '')
    .trim()
    .toLowerCase();
  if (!IN_FLIGHT_PHASES.has(phase)) {
    return null;
  }
  const taskId = run?.task_id?.trim();
  const task = taskId ? input.tasks?.find((row) => row.task_id === taskId) ?? null : null;
  if (taskIsVerificationHandoff(task)) {
    return 'Headless verification shift — scoped terminal jobs run npm test / verify scripts';
  }
  return 'Headless shift — shell commands require axon-agent-terminal-job on a scoped task';
}
