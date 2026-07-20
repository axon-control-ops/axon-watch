import { computed, type ComputedRef, type Ref } from 'vue';

import { buildIdeQuickGuide, type IdeQuickGuideActionId } from '../lib/ide-quick-guide';
import { isLegacyConnectorGlanceVisible } from '../lib/connector-glance-view';
import {
  buildIdeEditorStatusAgentChip,
  buildIdeEditorStatusConnectorChip,
  buildIdeEditorStatusTerminalChip,
} from '../lib/ide-editor-status-view';
import type { AgentDockReopenState } from '../lib/agent-dock-reopen-view';
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

  const ideQuickGuide = computed(() =>
    buildIdeQuickGuide({
      layoutMode: workbenchLayoutMode.value,
      agentDockCollapsed: shell.agentDockCollapsed,
      terminalVisible: terminalPanelVisible.value,
      pendingApprovals: shell.pendingApprovalsCount,
      streaming: shell.agentStreamActive,
      runPhase: shell.primaryActiveRun?.phase ?? null,
      employeeFailureLine: shell.activeIdeEmployeeFailureLine,
      employeeShiftInterrupted: shell.activeIdeEmployeeShiftInterrupted,
      requiredConnectorsUnavailable: shell.connectorsSummary?.required_unavailable ?? 0,
      legacyConnectorGlanceVisible: isLegacyConnectorGlanceVisible({
        connectorsLoadState: shell.connectorsLoadState,
        items: shell.connectorsItems,
        summary: shell.connectorsSummary,
        watchConnected: shell.runtimeSummary?.watch.connected ?? false,
        layoutMode: workbenchLayoutMode.value,
      }),
    }),
  );

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

  input.showTerminalPanel();
}
