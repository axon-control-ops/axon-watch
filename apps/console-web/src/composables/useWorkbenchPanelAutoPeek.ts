import { ref, watch, type ComputedRef, type Ref } from 'vue';

import {
  shouldAutoPeekAgentDock,
  shouldAutoPeekAgentDockForEmployeeFailure,
  shouldAutoPeekAgentDockForRun,
  shouldAutoPeekAgentDockForStreaming,
} from '../lib/agent-dock-auto-peek';
import { shouldAutoPeekWorkbenchTerminal } from '../lib/workbench-terminal-auto-peek';
import { employeeFailurePeekKey } from '../features/workspace-agents/company-roster-view';
import { useShellStore } from '../stores/shell';

type ShellStore = ReturnType<typeof useShellStore>;

/** Auto-open terminal and agent dock panels once when IDE work needs them. */
export function useWorkbenchPanelAutoPeek(input: {
  shell: ShellStore;
  workbenchLayoutMode: ComputedRef<'operator' | 'ide'>;
  terminalPanelVisible: Ref<boolean>;
  onShowTerminal: () => void;
  onShowAgentDock: () => void;
}): void {
  const { shell, workbenchLayoutMode, terminalPanelVisible, onShowTerminal, onShowAgentDock } =
    input;

  const autoPeekedTerminalRunIds = ref(new Set<string>());
  const autoPeekedAgentApprovalCount = ref(0);
  const autoPeekedAgentStreamMessageIds = ref(new Set<string>());
  const autoPeekedAgentRunIds = ref(new Set<string>());
  const autoPeekedAgentFailureKeys = ref(new Set<string>());

  watch(
    () =>
      [
        workbenchLayoutMode.value,
        terminalPanelVisible.value,
        shell.primaryActiveRun?.run_id ?? null,
        shell.primaryActiveRun?.phase ?? null,
      ] as const,
    ([layoutMode, terminalVisible, runId, runPhase]) => {
      if (
        !shouldAutoPeekWorkbenchTerminal({
          layoutMode,
          terminalVisible,
          runId,
          runPhase,
          alreadyPeekedRunIds: autoPeekedTerminalRunIds.value,
        })
      ) {
        return;
      }

      autoPeekedTerminalRunIds.value = new Set([
        ...autoPeekedTerminalRunIds.value,
        runId ?? '',
      ]);
      onShowTerminal();
    },
    { immediate: true },
  );

  watch(
    () =>
      [
        workbenchLayoutMode.value,
        shell.agentDockCollapsed,
        shell.pendingApprovalsCount,
        shell.agentStreamActive,
        shell.agentStreamMessageId,
        shell.primaryActiveRun?.run_id ?? null,
        shell.primaryActiveRun?.phase ?? null,
        shell.activeIdeEmployeeFailureLine,
        shell.activeIdeEmployeeRecord?.employee_id ?? null,
        shell.activeIdeEmployeeRecord?.last_run_id ?? null,
        shell.activeIdeEmployeeRecord?.last_outcome_detail ?? null,
      ] as const,
    ([
      layoutMode,
      agentDockCollapsed,
      pendingApprovals,
      streaming,
      streamMessageId,
      runId,
      runPhase,
      employeeFailureLine,
    ]) => {
      if (pendingApprovals === 0) {
        autoPeekedAgentApprovalCount.value = 0;
      }

      if (
        shouldAutoPeekAgentDock({
          layoutMode,
          agentDockCollapsed,
          pendingApprovals,
          lastPeekedApprovalCount: autoPeekedAgentApprovalCount.value,
        })
      ) {
        autoPeekedAgentApprovalCount.value = pendingApprovals;
        onShowAgentDock();
        return;
      }

      if (
        shouldAutoPeekAgentDockForStreaming({
          layoutMode,
          agentDockCollapsed,
          streaming,
          streamMessageId,
          alreadyPeekedStreamMessageIds: autoPeekedAgentStreamMessageIds.value,
        })
      ) {
        autoPeekedAgentStreamMessageIds.value = new Set([
          ...autoPeekedAgentStreamMessageIds.value,
          streamMessageId ?? '',
        ]);
        onShowAgentDock();
        return;
      }

      const failurePeekKey = shell.activeIdeEmployeeRecord
        ? employeeFailurePeekKey(shell.activeIdeEmployeeRecord)
        : null;

      if (
        shouldAutoPeekAgentDockForEmployeeFailure({
          layoutMode,
          agentDockCollapsed,
          employeeFailureLine,
          employeeFailurePeekKey: failurePeekKey,
          agentStreamActive: streaming,
          alreadyPeekedFailureKeys: autoPeekedAgentFailureKeys.value,
        })
      ) {
        autoPeekedAgentFailureKeys.value = new Set([
          ...autoPeekedAgentFailureKeys.value,
          failurePeekKey ?? '',
        ]);
        onShowAgentDock();
        return;
      }

      if (
        !shouldAutoPeekAgentDockForRun({
          layoutMode,
          agentDockCollapsed,
          runId,
          runPhase,
          alreadyPeekedRunIds: autoPeekedAgentRunIds.value,
        })
      ) {
        return;
      }

      autoPeekedAgentRunIds.value = new Set([...autoPeekedAgentRunIds.value, runId ?? '']);
      onShowAgentDock();
    },
    { immediate: true },
  );
}
