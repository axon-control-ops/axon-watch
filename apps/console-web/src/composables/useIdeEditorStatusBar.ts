import { computed, type ComputedRef, type Ref } from 'vue';

import { employeeComposerOpenPayload } from '../features/workspace-agents/company-roster-actions';
import {
  employeeDockReceiptRunId,
  employeeFailureRetryActionLabel,
} from '../features/workspace-agents/company-roster-view';
import { buildIdeQuickGuide, type IdeQuickGuideActionId } from '../lib/ide-quick-guide';
import {
  effectiveRequiredConnectorsUnavailable,
  isLegacyConnectorGlanceVisible,
} from '../lib/connector-glance-view';
import {
  buildIdeEditorStatusAgentChip,
  buildIdeEditorStatusConnectorChip,
  buildIdeEditorStatusTerminalChip,
} from '../lib/ide-editor-status-view';
import type { AgentDockReopenState } from '../lib/agent-dock-reopen-view';
import { focusAgentDockComposerInput } from '../lib/agent-dock-composer-focus';
import { requestIdeComposerMode } from '../lib/ide-composer-restore-request';
import { useShellStore } from '../stores/shell';

type ShellStore = ReturnType<typeof useShellStore>;

export function useIdeEditorStatusBar(input: {
  shell: ShellStore;
  workbenchLayoutMode: ComputedRef<'operator' | 'ide'>;
  terminalPanelVisible: Ref<boolean>;
  terminalReopenRunPhase: ComputedRef<string | null>;
  agentDockReopenState: ComputedRef<AgentDockReopenState>;
}) {
  const {
    shell,
    workbenchLayoutMode,
    terminalPanelVisible,
    terminalReopenRunPhase,
    agentDockReopenState,
  } = input;

  const ideEditorStatusTerminalChip = computed(() =>
    buildIdeEditorStatusTerminalChip({
      terminalVisible: terminalPanelVisible.value,
      runPhase: terminalReopenRunPhase.value,
    }),
  );

  const ideEditorStatusAgentChip = computed(() =>
    buildIdeEditorStatusAgentChip({
      agentDockCollapsed: shell.agentDockCollapsed,
      state: agentDockReopenState.value,
    }),
  );

  const ideEditorStatusConnectorChip = computed(() =>
    buildIdeEditorStatusConnectorChip({
      connectorsLoadState: shell.connectorsLoadState,
      items: shell.connectorsItems,
      summary: shell.connectorsSummary,
      watchConnected: shell.runtimeSummary?.watch.connected ?? false,
    }),
  );

  const ideQuickGuide = computed(() => {
    const watchConnected = shell.runtimeSummary?.watch.connected ?? false;
    const employee = shell.activeIdeEmployeeRecord;
    return buildIdeQuickGuide({
      layoutMode: workbenchLayoutMode.value,
      agentDockCollapsed: shell.agentDockCollapsed,
      terminalVisible: terminalPanelVisible.value,
      pendingApprovals: shell.pendingApprovalsCount,
      streaming: shell.agentStreamActive,
      runPhase: shell.primaryActiveRun?.phase ?? null,
      employeeFailureLine: shell.activeIdeEmployeeFailureLine,
      employeeShiftInterrupted: shell.activeIdeEmployeeShiftInterrupted,
      employeeRetryActionLabel: employee ? employeeFailureRetryActionLabel(employee) : null,
      employeeHasReceipts: employee ? Boolean(employeeDockReceiptRunId(employee)) : false,
      requiredConnectorsUnavailable: effectiveRequiredConnectorsUnavailable(
        shell.connectorsSummary,
        watchConnected,
      ),
      legacyConnectorGlanceVisible: isLegacyConnectorGlanceVisible({
        connectorsLoadState: shell.connectorsLoadState,
        items: shell.connectorsItems,
        summary: shell.connectorsSummary,
        watchConnected,
        layoutMode: workbenchLayoutMode.value,
      }),
      watchConnected,
    });
  });

  return {
    ideEditorStatusTerminalChip,
    ideEditorStatusAgentChip,
    ideEditorStatusConnectorChip,
    ideQuickGuide,
  };
}

export function openWatchConnectors(shell: ShellStore): void {
  void shell.loadConnectors();
  shell.focusWatchConnectors();
}

function openEmployeeComposerAction(
  shell: ShellStore,
  showAgentDock: () => void,
  kind: 'retry' | 'receipts',
): void {
  const row = shell.activeIdeEmployeeRecord;
  if (!row) {
    return;
  }

  showAgentDock();
  const { mode, draft } = employeeComposerOpenPayload(row, kind);
  requestIdeComposerMode(mode);
  if (draft) {
    shell.openIdeComposerWithDraft(draft, { keepActivityView: true });
  } else {
    shell.openIdeComposer({ keepActivityView: true });
  }
  focusAgentDockComposerInput();
}

export function handleIdeQuickGuideAction(
  actionId: IdeQuickGuideActionId,
  input: {
    shell: ShellStore;
    showAgentDock: () => void;
    showTerminalPanel: () => void;
  },
): void {
  if (actionId === 'retry-employee-shift') {
    openEmployeeComposerAction(input.shell, input.showAgentDock, 'retry');
    return;
  }

  if (actionId === 'view-employee-receipts') {
    openEmployeeComposerAction(input.shell, input.showAgentDock, 'receipts');
    return;
  }

  if (actionId === 'open-team-roster') {
    input.shell.revealTeamRosterForActiveEmployee();
    return;
  }

  if (actionId === 'expand-agent-dock') {
    input.showAgentDock();
    return;
  }

  if (actionId === 'open-connectors') {
    openWatchConnectors(input.shell);
    return;
  }

  input.showTerminalPanel();
}
