import { computed, type ComputedRef, type Ref } from 'vue';

import { buildCompanyRosterAlertBadge } from '../features/workspace-agents/company-roster-failure-view';
import {
  companyFailedEmployees,
  companyFailedEmployeesHint,
  employeeFailureRetryActionLabel,
} from '../features/workspace-agents/company-roster-view';
import type { AgentDockReopenState } from '../lib/agent-dock-reopen-view';
import {
  effectiveRequiredConnectorsUnavailable,
  isLegacyConnectorGlanceVisible,
} from '../lib/connector-glance-view';
import { countIdeDirtyFileTabs } from '../lib/ide-activity-panel-view';
import type { IdeLayoutShortcutAction } from '../lib/ide-layout-shortcuts';
import { buildIdeQuickGuide, type IdeQuickGuideActionId } from '../lib/ide-quick-guide';
import {
  buildIdeEditorStatusAgentChip,
  buildIdeEditorStatusConnectorChip,
  buildIdeEditorStatusGitChip,
  buildIdeEditorStatusProblemsChip,
  buildIdeEditorStatusSearchChip,
  buildIdeEditorStatusTeamChip,
  buildIdeEditorStatusTerminalChip,
} from '../lib/ide-editor-status-view';
import { buildWorkbenchProblemItems } from '../lib/workbench-problem-items';
import { navigateToSettingsSection } from '../lib/settings-section-route';
import { runEmployeeShiftRetry } from '../lib/run-employee-shift-retry';
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

  const sourceControlExpanded = computed(
    () => shell.ideActivityView === 'git' && !shell.ideExplorerCollapsed,
  );

  const searchExpanded = computed(
    () => shell.ideActivityView === 'search' && !shell.ideExplorerCollapsed,
  );

  const teamExpanded = computed(
    () => shell.ideActivityView === 'team' && !shell.ideExplorerCollapsed,
  );

  const ideEditorStatusGitChip = computed(() =>
    buildIdeEditorStatusGitChip({
      dirtyFileCount: countIdeDirtyFileTabs(shell.editorDocuments),
      sourceControlExpanded: sourceControlExpanded.value,
    }),
  );

  const ideEditorStatusSearchChip = computed(() =>
    buildIdeEditorStatusSearchChip({
      loadState: shell.workspaceFilesLoadState,
      hasWorkspace: Boolean(shell.currentWorkspace?.workspace_id),
      searchExpanded: searchExpanded.value,
    }),
  );

  const ideEditorStatusTeamChip = computed(() =>
    buildIdeEditorStatusTeamChip({
      employees: shell.companyEmployeesForCurrentWorkspace,
      teamExpanded: teamExpanded.value,
    }),
  );

  const ideEditorStatusProblemsChip = computed(() =>
    buildIdeEditorStatusProblemsChip({
      problemCount: buildWorkbenchProblemItems(shell).length,
      terminalVisible: terminalPanelVisible.value,
    }),
  );

  const ideQuickGuide = computed(() => {
    const watchConnected = shell.runtimeSummary?.watch.connected ?? false;
    const employee = shell.activeIdeEmployeeRecord;
    const employeeFailureLine = shell.activeIdeEmployeeFailureLine;
    const rosterEmployees = shell.companyEmployeesForCurrentWorkspace;
    const failedEmployeeCount = companyFailedEmployees(rosterEmployees).length;
    const failedEmployeesHint = companyFailedEmployeesHint(rosterEmployees);
    const rosterAlertTone = buildCompanyRosterAlertBadge(rosterEmployees)?.tone ?? null;
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
      watchConnected,
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
      failedEmployeeCount,
      failedEmployeesHint,
      rosterAlertTone,
      dirtyFileCount: countIdeDirtyFileTabs(shell.editorDocuments),
      sourceControlExpanded: sourceControlExpanded.value,
      workspaceFilesLoadState: shell.workspaceFilesLoadState,
      searchExpanded: searchExpanded.value,
      teamExpanded: teamExpanded.value,
      problemCount: buildWorkbenchProblemItems(shell).length,
    });
  });

  return {
    ideEditorStatusTerminalChip,
    ideEditorStatusAgentChip,
    ideEditorStatusConnectorChip,
    ideEditorStatusGitChip,
    ideEditorStatusSearchChip,
    ideEditorStatusTeamChip,
    ideEditorStatusProblemsChip,
    ideQuickGuide,
  };
}

/** Load or retry the workspace file index before Search or Explorer lists paths. */
export function ensureWorkspaceFilesLoaded(shell: ShellStore): void {
  if (!shell.currentWorkspace?.workspace_id) {
    return;
  }

  if (
    shell.workspaceFilesLoadState === 'idle' ||
    shell.workspaceFilesLoadState === 'error'
  ) {
    void shell.loadWorkspaceFiles();
  }
}

/** Warm or refresh watch connector probes before surfacing connector-attention UI. */
export function ensureWatchConnectorsLoaded(shell: ShellStore): void {
  if (shell.connectorsLoadState === 'idle') {
    void shell.loadConnectors();
    return;
  }

  if (shell.connectorsLoadState === 'loaded') {
    void shell.loadConnectors({ background: true });
  }
}

export function openWatchConnectors(shell: ShellStore): void {
  ensureWatchConnectorsLoaded(shell);
  shell.focusWatchConnectors();
}

/** Open Source Control in the left sidebar (status bar chip, quick guide, shortcuts). */
export function openIdeSourceControl(shell: ShellStore): void {
  shell.focusIdeSidebarView('git');
}

/** Open Search in the left sidebar and warm the workspace file index when needed. */
export function openIdeSearch(shell: ShellStore): void {
  ensureWorkspaceFilesLoaded(shell);
  shell.focusIdeSidebarView('search');
}

/** Open Team in the left sidebar (status bar chip, quick guide). */
export function openIdeTeam(shell: ShellStore): void {
  shell.focusIdeSidebarView('team');
}

/** Open Settings → CLI runtime for Cursor/Claude usage cards. */
export function openRuntimeUsageSettings(shell: ShellStore): void {
  if (shell.runtimeStatusLoadState === 'idle') {
    void shell.loadRuntimeStatus();
  }
  navigateToSettingsSection('runtime');
}

/** Apply a resolved IDE layout keyboard shortcut through the same entry points as chips and quick guide. */
export function handleIdeLayoutShortcutAction(
  action: IdeLayoutShortcutAction,
  shell: ShellStore,
): void {
  if (action === 'toggle-explorer') {
    shell.toggleIdeExplorer();
    return;
  }

  if (action === 'toggle-agent-dock') {
    shell.toggleAgentDock();
    return;
  }

  if (action === 'open-source-control') {
    openIdeSourceControl(shell);
    return;
  }

  if (action === 'open-search') {
    openIdeSearch(shell);
    return;
  }

  shell.toggleIdeTerminalPanel();
}

export async function openEmployeeShiftRetry(input: {
  shell: ShellStore;
  showAgentDock: () => void;
}): Promise<void> {
  const employee = input.shell.activeIdeEmployeeRecord;
  if (!employee) {
    return;
  }

  input.showAgentDock();
  await runEmployeeShiftRetry(input.shell, employee, {
    keepActivityView: true,
    focusThread: true,
  });
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

  if (actionId === 'open-team') {
    openIdeTeam(input.shell);
    return;
  }

  if (actionId === 'open-source-control') {
    openIdeSourceControl(input.shell);
    return;
  }

  if (actionId === 'open-search') {
    openIdeSearch(input.shell);
    return;
  }

  if (actionId === 'retry-employee-shift') {
    void openEmployeeShiftRetry(input);
    return;
  }

  if (actionId === 'show-problems') {
    input.shell.revealIdeWorkbenchProblems();
    return;
  }

  input.showTerminalPanel();
}
