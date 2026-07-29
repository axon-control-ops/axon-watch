/** Shared employee-shift failure actions for the IDE composer review strip. */

import { computed, ref, type ComputedRef, type Ref } from 'vue';

import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import { employeeComposerOpenPayload } from '../../features/workspace-agents/company-roster-actions';
import {
  employeeDockReceiptRunId,
  employeeFailureRetryActionLabel,
  employeeShiftNeedsContinuation,
} from '../../features/workspace-agents/company-roster-view';
import { focusAgentDockComposerInput } from '../../lib/agent-dock-composer-focus';
import { requestIdeComposerMode } from '../../lib/ide-composer-restore-request';
import { shouldSurfaceIdeEmployeeFailure } from '../../lib/ide-presence-profile';
import { runEmployeeShiftRetry } from '../../lib/run-employee-shift-retry';
import type { useShellStore } from '../../stores/shell';

type ShellStore = ReturnType<typeof useShellStore>;

export function useEmployeeFailureStripActions(shell: ShellStore): {
  retrying: Ref<boolean>;
  showFailureActions: ComputedRef<boolean>;
  showRetryAction: ComputedRef<boolean>;
  showExplainAction: ComputedRef<boolean>;
  interruptedShift: ComputedRef<boolean>;
  retryLabel: ComputedRef<string>;
  actionsDisabled: ComputedRef<boolean>;
  handleRetry: () => Promise<void>;
  handleExplain: () => void;
  handleOpenTeam: () => void;
} {
  const retrying = ref(false);

  const employee = computed(() => shell.activeIdeEmployeeRecord);
  const failureLine = computed(() => shell.activeIdeEmployeeFailureLine);

  const showFailureActions = computed(
    () =>
      shouldSurfaceIdeEmployeeFailure({
        profileState: shell.ideDisplayKairoPresenceState,
        employeeFailureLine: failureLine.value,
        agentStreamActive: shell.agentStreamActive,
        kairoSpeechActive: shell.kairoSpeechActive,
      }) && Boolean(employee.value),
  );

  /** Try again / Continue only when the last job failed or was interrupted — never after success. */
  const showRetryAction = computed(() => showFailureActions.value);

  const showExplainAction = computed(() =>
    employee.value ? Boolean(employeeDockReceiptRunId(employee.value)) : false,
  );

  const interruptedShift = computed(() =>
    employee.value ? employeeShiftNeedsContinuation(employee.value) : false,
  );

  const retryLabel = computed(() =>
    employee.value ? employeeFailureRetryActionLabel(employee.value) : 'Try again',
  );

  const actionsDisabled = computed(
    () => shell.composerAgentBusy || retrying.value,
  );

  function openComposerDraft(
    row: CompanyEmployeeRecord,
    kind: 'receipts',
  ): void {
    const { mode, draft } = employeeComposerOpenPayload(row, kind);
    if (mode) {
      requestIdeComposerMode(mode);
    }
    if (draft) {
      shell.openIdeComposerWithDraft(draft, { keepActivityView: true });
    } else {
      shell.openIdeComposer({ keepActivityView: true });
    }
    focusAgentDockComposerInput();
  }

  function handleExplain(): void {
    const row = employee.value;
    if (!row) {
      return;
    }
    openComposerDraft(row, 'receipts');
  }

  function handleOpenTeam(): void {
    shell.revealTeamRosterForActiveEmployee();
  }

  async function handleRetry(): Promise<void> {
    const row = employee.value;
    if (!row || actionsDisabled.value || !showRetryAction.value) {
      return;
    }
    retrying.value = true;
    try {
      const result = await runEmployeeShiftRetry(shell, row, {
        keepActivityView: true,
        focusThread: true,
      });
      if (!result.ok) {
        shell.commandMutationError = result.reason;
      }
    } finally {
      retrying.value = false;
    }
  }

  return {
    retrying,
    showFailureActions,
    showRetryAction,
    showExplainAction,
    interruptedShift,
    retryLabel,
    actionsDisabled,
    handleRetry,
    handleExplain,
    handleOpenTeam,
  };
}
