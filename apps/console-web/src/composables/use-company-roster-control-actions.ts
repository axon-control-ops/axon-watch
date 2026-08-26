import { ref, type Ref } from 'vue';

import type { CompanyEmployeeRecord } from '../contracts/canonical';
import {
  clearWorkspaceEmployeeRunCard,
  patchWorkspaceEmployeeEnabled,
} from '../api/worker-scheduler-api';
import { stopRun } from '../api/runs-api';
import type { TeamMemberQuickAction } from '../features/workspace-agents/company-roster-actions';
import { resolveEmployeeManualHandoff } from '../features/workspace-agents/employee-manual-handoff';
import { resolveOperatorStartAction } from '../lib/verification-handoff';
import type { useShellStore } from '../stores/shell';

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
    if (action.control === 'clear_run_card') {
      const workspaceId = input.currentWorkspaceId.value?.trim();
      if (!workspaceId) {
        return;
      }
      controlBusyId.value = employee.employee_id;
      controlError.value = null;
      try {
        await clearWorkspaceEmployeeRunCard(workspaceId, employee.employee_id);
        await Promise.all([
          input.loadCompany(),
          input.shell.loadRuns({ sync: false }),
        ]);
      } catch (error) {
        controlError.value =
          error instanceof Error ? error.message : 'Could not clear agent run card';
      } finally {
        controlBusyId.value = null;
      }
      return;
    }
    if (action.control === 'start_now') {
      const workspaceId = input.currentWorkspaceId.value?.trim();
      controlBusyId.value = employee.employee_id;
      controlError.value = null;
      try {
        if (workspaceId) {
          await Promise.all([
            input.shell.loadWorkspaceTasks(workspaceId),
            input.shell.loadRuns({ sync: false }),
          ]);
        }
        const tasks = input.shell.workspaceTasksForCurrentWorkspace;
        const handoff = resolveEmployeeManualHandoff({
          employee,
          autonomyMode: input.shell.operatorPresenceSettings.autonomy_mode,
          tasks,
          runs: input.shell.runs,
          liveBusy: false,
        });
        const resolved = resolveOperatorStartAction({
          employee,
          tasks,
          runs: input.shell.runs,
          handoffTaskId: handoff.waiting ? handoff.taskId : null,
          liveBusy: false,
        });
        const taskId = resolved?.taskId?.trim() ?? action.taskId?.trim();
        if (!taskId) {
          controlError.value = 'No handoff task is bound to Start now. Refresh the team roster.';
          return;
        }
        const verificationRun = resolved?.label === 'Run verification';
        const started = await input.shell.startCurrentWorkspaceTask(taskId);
        if (!started) {
          controlError.value =
            input.shell.workspaceTasksError || 'Could not start handoff';
          return;
        }
        if (!started.runId) {
          controlError.value = 'Handoff start returned no run. Refresh and try again.';
          return;
        }
        const phase = (started.runPhase ?? '').trim().toLowerCase();
        // Dispatch success is anything past queued. `starting`/`planning` are mid-kick
        // phases — treating them as failure left the run live while the button looked dead.
        if (!phase || phase === 'queued') {
          controlError.value =
            'Handoff is still queued; worker dispatch did not start. Check capacity and try again.';
          return;
        }
        await Promise.all([
          input.loadCompany(),
          workspaceId
            ? input.shell.loadCompanyEmployees(workspaceId)
            : Promise.resolve(),
          input.shell.loadRuns({ sync: false }),
        ]);

        const focusStartedHandoff = async (): Promise<void> => {
          const preferredThread = started.threadId?.trim() || '';
          let threadId: string | null = null;
          const forceRefresh = !verificationRun;
          if (preferredThread) {
            await input.shell.selectIdeThread(preferredThread, { forceRefresh });
            input.shell.openIdeComposer({ keepActivityView: true });
            threadId = preferredThread;
          } else {
            threadId = await input.shell.openOrFocusEmployeeIdeThread(employee, {
              forceRefresh,
            });
          }
          if (!threadId) {
            controlError.value = 'Handoff started, but its IDE thread could not be opened.';
            return;
          }
          if (workspaceId) {
            await input.shell.rehydrateWorkspaceIdeStreams(workspaceId);
          }
          input.shell.setLayoutMode('ide');
        };

        if (verificationRun) {
          // Verification threads can carry huge npm/Jest scrollback — defer IDE mount
          // so the Team panel stays responsive while the shift kicks off.
          globalThis.setTimeout(() => {
            void focusStartedHandoff().catch((error) => {
              controlError.value =
                error instanceof Error ? error.message : 'Could not open verification thread';
            });
          }, 0);
          return;
        }

        await focusStartedHandoff();
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
