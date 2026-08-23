import { computed, type ComputedRef, type Ref } from 'vue';

import type { CompanyEmployeeRecord } from '../contracts/canonical';
import { resolveEmployeeManualHandoff } from '../features/workspace-agents/employee-manual-handoff';
import {
  employeeQuickActions,
  type TeamMemberQuickAction,
} from '../features/workspace-agents/company-roster-actions';
import type { useShellStore } from '../stores/shell';

type ShellStore = ReturnType<typeof useShellStore>;

function resolveHandoff(employee: CompanyEmployeeRecord, input: {
  shell: ShellStore;
  liveBusy: boolean;
}) {
  return resolveEmployeeManualHandoff({
    employee,
    autonomyMode: input.shell.operatorPresenceSettings.autonomy_mode,
    tasks: input.shell.workspaceTasksForCurrentWorkspace,
    runs: input.shell.runs,
    liveBusy: input.liveBusy,
  });
}

/** Quick actions + manual-handoff-waiting state for the selected/roster employees. */
export function useCompanyRosterQuickActionState(input: {
  shell: ShellStore;
  employees: Ref<CompanyEmployeeRecord[]>;
  selectedEmployee: Ref<CompanyEmployeeRecord | null>;
  liveBusyEmployeeIds: Ref<string[]>;
}): {
  selectedActions: ComputedRef<TeamMemberQuickAction[]>;
  handoffWaitingEmployeeIds: ComputedRef<string[]>;
  selectedHandoffBlockedReason: ComputedRef<string | null>;
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
    const liveBusy = new Set(input.liveBusyEmployeeIds.value);
    return input.employees.value
      .filter((employee) =>
        resolveHandoff(employee, {
          shell: input.shell,
          liveBusy: liveBusy.has(employee.employee_id),
        }).waiting,
      )
      .map((employee) => employee.employee_id);
  });

  const selectedHandoffBlockedReason = computed(() => {
    const employee = input.selectedEmployee.value;
    if (!employee) {
      return null;
    }
    return (
      resolveHandoff(employee, {
        shell: input.shell,
        liveBusy: input.liveBusyEmployeeIds.value.includes(employee.employee_id),
      }).blockedReason ?? null
    );
  });

  return { selectedActions, handoffWaitingEmployeeIds, selectedHandoffBlockedReason };
}
