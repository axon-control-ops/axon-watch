import { computed, type ComputedRef, type Ref } from 'vue';

import type { CompanyEmployeeRecord } from '../contracts/canonical';
import { resolveEmployeeManualHandoff } from '../features/workspace-agents/employee-manual-handoff';
import {
  employeeQuickActions,
  type TeamMemberQuickAction,
} from '../features/workspace-agents/company-roster-actions';
import type { useShellStore } from '../stores/shell';

type ShellStore = ReturnType<typeof useShellStore>;

/** Quick actions + manual-handoff-waiting state for the selected/roster employees. */
export function useCompanyRosterQuickActionState(input: {
  shell: ShellStore;
  employees: Ref<CompanyEmployeeRecord[]>;
  selectedEmployee: Ref<CompanyEmployeeRecord | null>;
  liveBusyEmployeeIds: Ref<string[]>;
}): {
  selectedActions: ComputedRef<TeamMemberQuickAction[]>;
  handoffWaitingEmployeeIds: ComputedRef<string[]>;
} {
  const selectedActions = computed(() =>
    input.selectedEmployee.value
      ? employeeQuickActions(input.selectedEmployee.value, {
          autonomyMode: input.shell.operatorPresenceSettings.autonomy_mode,
          tasks: input.shell.workspaceTasksForCurrentWorkspace,
          runs: input.shell.runs,
          liveBusy: input.liveBusyEmployeeIds.value.includes(
            input.selectedEmployee.value.employee_id,
          ),
        })
      : [],
  );

  const handoffWaitingEmployeeIds = computed(() => {
    const mode = input.shell.operatorPresenceSettings.autonomy_mode;
    const tasks = input.shell.workspaceTasksForCurrentWorkspace;
    const runs = input.shell.runs;
    const liveBusy = new Set(input.liveBusyEmployeeIds.value);
    return input.employees.value
      .filter((employee) =>
        resolveEmployeeManualHandoff({
          employee,
          autonomyMode: mode,
          tasks,
          runs,
          liveBusy: liveBusy.has(employee.employee_id),
        }).waiting,
      )
      .map((employee) => employee.employee_id);
  });

  return { selectedActions, handoffWaitingEmployeeIds };
}
