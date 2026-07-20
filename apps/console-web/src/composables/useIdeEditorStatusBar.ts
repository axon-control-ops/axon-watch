import { computed, type ComputedRef, type Ref } from 'vue';

import { employeeComposerOpenPayload } from '../features/workspace-agents/company-roster-actions';
import { employeeFailureRetryActionLabel } from '../features/workspace-agents/company-roster-view';
import { focusAgentDockComposerInput } from '../lib/agent-dock-composer-focus';
import type { AgentDockReopenState } from '../lib/agent-dock-reopen-view';
import {
  effectiveRequiredConnectorsUnavailable,
  isLegacyConnectorGlanceVisible,
} from '../lib/connector-glance-view';
import { requestIdeComposerMode } from '../lib/ide-composer-restore-request';
import { buildIdeQuickGuide, type IdeQuickGuideActionId } from '../lib/ide-quick-guide';
import {
  buildIdeEditorStatusAgentChip,
  buildIdeEditorStatusConnectorChip,
  buildIdeEditorStatusTerminalChip,
} from '../lib/ide-editor-status-view';
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
    const employeeFailureLine = shell.activeIdeEmployeeFailureLine;
    return buildIdeQuickGuide({
      layoutMode: workbenchLayoutMode.value,
      agentDockCollapsed: shell.agentDockCollapsed,
      terminalVisible: terminalPanelVisible.value,
      pendingApprovals: shell.pendingApprovalsCount,
      streaming: shell.agentStreamActive,
      runPhase: shell.primaryActiveRun?.phase ?? null,
      employeeFailureLine,
      employeeShiftInterrupted: shell.activeIdeEmployeeShiftInterrupted,
      employeeRetryActionLabel:
        employee && (employeeFailureLine ?? '').trim()
          ? employeeFailureRetryActionLabel(employee)
          : null,
      requiredConnectorsUnavailable: effectiveRequiredConnectorsUnavailable(
        shell.connectorsSummary,
        watchConnected,
      ),
      legacyConnectorGlanceVisible: isLegacyConnectorGlanceVisible({
        connectorsLoadState: shell.connectorsLoadState,
        items: shell.connectorsItems,
        summary: shell.connectorsSummary,
        watchConnected: shell.runtimeSummary?.watch.connected ?? false,
        layoutMode: workbenchLayoutMode.value,
      }),
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

export function openEmployeeShiftRetry(input: {
  shell: ShellStore;
  showAgentDock: () => void;
}): void {
  const employee = input.shell.activeIdeEmployeeRecord;
  if (!employee) {
    return;
  }

  input.showAgentDock();
  const { mode, draft } = employeeComposerOpenPayload(employee, 'retry');
  requestIdeComposerMode(mode);
  if (draft) {
    input.shell.openIdeComposerWithDraft(draft, { keepActivityView: true });
  } else {
    input.shell.openIdeComposer({ keepActivityView: true });
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
  if (actionId === 'expand-agent-dock') {
    input.showAgentDock();
    return;
  }

  if (actionId === 'open-connectors') {
    openWatchConnectors(input.shell);
    return;
  }

  if (actionId === 'retry-employee-shift') {
    openEmployeeShiftRetry(input);
    return;
  }

  input.showTerminalPanel();
}
