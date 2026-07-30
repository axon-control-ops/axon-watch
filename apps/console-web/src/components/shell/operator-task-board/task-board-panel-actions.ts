import type { CompanyEmployeeRecord } from '../../../contracts/canonical';
import type { TaskBoardRow } from '../../../lib/operator-task-board-view';
import { parseDependencies } from './operator-task-board-helpers';

type ShellTaskBoard = {
  fanOutCurrentWorkspaceLeadPlan: (input: {
    goal: string;
    mode: 'auto';
    create_runs: boolean;
  }) => Promise<unknown>;
  createCurrentWorkspaceTask: (input: {
    goal: string;
    owner_role: string;
    acceptance_criteria: string;
    risk: string;
    attempt_budget: number;
    dependencies: string[];
  }) => Promise<{ task_id: string } | null | undefined>;
  loadWorkspaceTasks: (workspaceId: string) => Promise<unknown>;
  currentWorkspace?: { workspace_id?: string } | null;
  runs: ReadonlyArray<{ run_id?: string; employee_role?: string | null }>;
  companyEmployeesForCurrentWorkspace: ReadonlyArray<CompanyEmployeeRecord>;
  openOrFocusEmployeeIdeThread: (
    employee: Pick<CompanyEmployeeRecord, 'employee_id' | 'name' | 'role'> & {
      role_label?: string;
    },
    options?: { forceRefresh?: boolean },
  ) => Promise<string | null>;
  setLayoutMode: (mode: 'ide') => void;
};

export async function submitTaskBoardCreate(input: {
  shell: ShellTaskBoard;
  createAsLeadPlan: boolean;
  goal: string;
  ownerRole: string;
  acceptance: string;
  risk: string;
  attemptBudget: number;
  dependenciesDraft: string;
  canCreate: boolean;
  refreshScheduler: () => Promise<void>;
}): Promise<{ selectedTaskId?: string; cleared: boolean }> {
  if (!input.canCreate) {
    return { cleared: false };
  }
  if (input.createAsLeadPlan) {
    const created = await input.shell.fanOutCurrentWorkspaceLeadPlan({
      goal: input.goal.trim(),
      mode: 'auto',
      create_runs: true,
    });
    if (created) {
      await input.shell.loadWorkspaceTasks(input.shell.currentWorkspace?.workspace_id ?? '');
      await input.refreshScheduler();
      return { cleared: true };
    }
    return { cleared: false };
  }
  const created = await input.shell.createCurrentWorkspaceTask({
    goal: input.goal.trim(),
    owner_role: input.ownerRole,
    acceptance_criteria: input.acceptance.trim(),
    risk: input.risk,
    attempt_budget: input.attemptBudget,
    dependencies: parseDependencies(input.dependenciesDraft),
  });
  if (created) {
    return { cleared: true, selectedTaskId: created.task_id };
  }
  return { cleared: false };
}

export function openTaskBoardAssociatedRun(input: {
  shell: ShellTaskBoard;
  row: TaskBoardRow;
  openSpecialist: (row: TaskBoardRow) => void | Promise<void>;
}): void {
  const { shell, row } = input;
  if (!row.runId) {
    return;
  }
  const run = shell.runs.find((item) => item.run_id === row.runId);
  if (run?.employee_role) {
    const employee = shell.companyEmployeesForCurrentWorkspace.find(
      (item) =>
        String(item.role || '').trim().toLowerCase() ===
        String(run.employee_role || '').trim().toLowerCase(),
    );
    if (employee) {
      void shell.openOrFocusEmployeeIdeThread(employee);
    }
  } else {
    void input.openSpecialist(row);
  }
  shell.setLayoutMode('ide');
}
