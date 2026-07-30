import { ref, type Ref } from 'vue';

import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import { patchWorkspaceEmployeeEnabled } from '../../api/worker-scheduler-api';
import { stopRun } from '../../api/runs-api';
import type { TeamMemberQuickAction } from '../../features/workspace-agents/company-roster-actions';
import type { useShellStore } from '../../stores/shell';

type ShellStore = ReturnType<typeof useShellStore>;

export function useCompanyRosterControlActions(input: {
  shell: ShellStore;
  currentWorkspaceId: Ref<string | null>;
  loadCompany: () => Promise<void>;
}): {
  controlBusyId: Ref<string | null>;
  controlError: Ref<string | null>;
  onControlAction: (
    employee: CompanyEmployeeRecord,
    action: TeamMemberQuickAction,
  ) => Promise<void>;
} {
  const controlBusyId = ref<string | null>(null);
  const controlError = ref<string | null>(null);

  async function onControlAction(
    employee: CompanyEmployeeRecord,
    action: TeamMemberQuickAction,
  ): Promise<void> {
    if (action.control === 'toggle_enabled') {
      const workspaceId = input.currentWorkspaceId.value?.trim();
      if (!workspaceId) {
        return;
      }
      controlBusyId.value = employee.employee_id;
      controlError.value = null;
      try {
        await patchWorkspaceEmployeeEnabled(
          workspaceId,
          employee.employee_id,
          !employee.enabled,
        );
        await input.loadCompany();
      } catch (error) {
        controlError.value =
          error instanceof Error ? error.message : 'Could not update agent enabled state';
      } finally {
        controlBusyId.value = null;
      }
      return;
    }
    if (action.control === 'stop') {
      const runId = employee.active_run_id?.trim();
      if (!runId) {
        return;
      }
      controlBusyId.value = employee.employee_id;
      controlError.value = null;
      try {
        await stopRun(runId);
        await input.loadCompany();
      } catch (error) {
        controlError.value = error instanceof Error ? error.message : 'Could not stop job';
      } finally {
        controlBusyId.value = null;
      }
      return;
    }
    if (action.control === 'start_now') {
      const taskId = action.taskId?.trim();
      if (!taskId) {
        return;
      }
      controlBusyId.value = employee.employee_id;
      controlError.value = null;
      try {
        const started = await input.shell.startCurrentWorkspaceTask(taskId);
        if (!started) {
          controlError.value =
            input.shell.workspaceTasksError || 'Could not start handoff';
          return;
        }
        await Promise.all([
          input.loadCompany(),
          input.shell.loadRuns({ sync: false }),
          input.shell.openOrFocusEmployeeIdeThread(employee, { forceRefresh: true }),
        ]);
        input.shell.setLayoutMode('ide');
      } catch (error) {
        controlError.value =
          error instanceof Error ? error.message : 'Could not start handoff';
      } finally {
        controlBusyId.value = null;
      }
    }
  }

  return { controlBusyId, controlError, onControlAction };
}
