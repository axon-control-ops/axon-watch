<script setup lang="ts">
import { computed, watch } from 'vue';

import { ensureWatchConnectorsLoaded } from '../../composables/useIdeEditorStatusBar';

import type { IdeActivityView } from '../../lib/ide-layout-prefs';
import { resolveIdeActivityBarSelectAction } from '../../lib/ide-activity-bar-select';
import {
  agentDockActivityBarAriaLabel,
  agentDockActivityBarTitle,
  agentDockReopenAlive,
  agentDockReopenEmployeeFailure,
  agentDockReopenEmployeeInterrupted,
} from '../../lib/agent-dock-reopen-view';
import {
  type IdeSidebarActivityView,
  buildIdeActivityBarTeamAttention,
  ideActivityBarGitAriaLabel,
  ideActivityBarGitNeedsAttention,
  ideActivityBarGitTitle,
  ideActivityBarRunAriaLabel,
  ideActivityBarRunNeedsAttention,
  ideActivityBarRunTitle,
  ideActivityBarSearchAriaLabel,
  ideActivityBarSearchNeedsAttention,
  ideActivityBarSearchTitle,
  ideActivityBarSidebarAriaLabel,
  ideActivityBarSidebarTitle,
  ideActivityBarTeamAriaLabel,
  ideActivityBarTeamTitle,
} from '../../lib/ide-activity-bar-view';
import {
  effectiveRequiredConnectorsUnavailable,
  isLegacyConnectorGlanceVisible,
} from '../../lib/connector-glance-view';
import {
  ideActivityBarTerminalAriaLabel,
  ideActivityBarTerminalTitle,
  workbenchTerminalPanelAlive,
} from '../../lib/workbench-terminal-panel-view';
import IdeActivityIcon from './IdeActivityIcon.vue';
import { navigateToAppSurface } from '../../lib/app-surface-route';
import { countIdeDirtyFileTabs } from '../../lib/ide-activity-panel-view';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

const watchConnected = computed(() => shell.runtimeSummary?.watch.connected ?? false);

const requiredConnectorsUnavailable = computed(() =>
  effectiveRequiredConnectorsUnavailable(shell.connectorsSummary, watchConnected.value),
);

const runConnectorAttention = computed(() => ({
  watchConnected: watchConnected.value,
  requiredConnectorsUnavailable: requiredConnectorsUnavailable.value,
  legacyConnectorGlanceVisible: isLegacyConnectorGlanceVisible({
    connectorsLoadState: shell.connectorsLoadState,
    items: shell.connectorsItems,
    summary: shell.connectorsSummary,
    watchConnected: watchConnected.value,
    layoutMode: shell.layoutMode,
  }),
}));

const runNeedsAttention = computed(() =>
  ideActivityBarRunNeedsAttention(runConnectorAttention.value),
);

const teamAttention = computed(() =>
  buildIdeActivityBarTeamAttention(shell.companyEmployeesForCurrentWorkspace),
);

const teamNeedsAttention = computed(() => teamAttention.value.count > 0);

const dirtyFileCount = computed(() => countIdeDirtyFileTabs(shell.editorDocuments));

const gitNeedsAttention = computed(() => ideActivityBarGitNeedsAttention(dirtyFileCount.value));

const searchHasWorkspace = computed(() => Boolean(shell.currentWorkspace?.workspace_id));

const searchAttentionInput = computed(() => ({
  loadState: shell.workspaceFilesLoadState,
  hasWorkspace: searchHasWorkspace.value,
}));

const searchNeedsAttention = computed(() =>
  ideActivityBarSearchNeedsAttention(searchAttentionInput.value),
);

watch(
  runNeedsAttention,
  (shouldRefresh) => {
    if (shouldRefresh) {
      ensureWatchConnectorsLoaded(shell);
    }
  },
  { immediate: true },
);

const attentionBadgeCount = computed(() => shell.leftSidebarAttentionBadgeCount);

const items: Array<{ id: IdeActivityView; label: string }> = [
  { id: 'team', label: 'Team' },
  { id: 'explorer', label: 'Explorer' },
  { id: 'search', label: 'Search' },
  { id: 'git', label: 'Source Control' },
  { id: 'run', label: 'Run' },
  { id: 'terminal', label: 'Terminal' },
  { id: 'agent', label: 'Agent Dock' },
];

function attentionTitle(): string {
  const count = attentionBadgeCount.value;
  const base = shell.ideAttentionPanelOpen
    ? 'Attention · Click to close'
    : 'Attention';
  return count > 0 ? `${base} · ${count} needing review` : base;
}

function attentionAriaLabel(): string {
  const count = attentionBadgeCount.value;
  if (shell.ideAttentionPanelOpen) {
    return count > 0
      ? `Close attention panel (${count} items)`
      : 'Close attention panel';
  }
  return count > 0
    ? `Open attention panel (${count} items)`
    : 'Open attention panel';
}

function selectAttention(): void {
  shell.toggleIdeAttentionPanel();
}

const agentDockExpanded = computed(() => !shell.agentDockCollapsed);

const agentDockState = computed(() => ({
  streaming: shell.agentStreamActive,
  pendingApprovals: shell.pendingApprovalsCount,
  runPhase: shell.primaryActiveRun?.phase ?? null,
  employeeFailureLine: shell.activeIdeEmployeeFailureLine,
  employeeShiftInterrupted: shell.activeIdeEmployeeShiftInterrupted,
  speaking: shell.kairoSpeechActive,
}));

const agentDockAlive = computed(() => agentDockReopenAlive(agentDockState.value));

const agentDockEmployeeFailure = computed(() =>
  agentDockReopenEmployeeFailure(agentDockState.value),
);

const agentDockEmployeeInterrupted = computed(() =>
  agentDockReopenEmployeeInterrupted(agentDockState.value),
);

const terminalRunPhase = computed(() => shell.primaryActiveRun?.phase ?? null);

const terminalAlive = computed(
  () =>
    !shell.workbenchTerminalPanelVisible &&
    workbenchTerminalPanelAlive(terminalRunPhase.value),
);

const sidebarViews = new Set<IdeSidebarActivityView>([
  'explorer',
  'search',
  'git',
  'run',
  'team',
]);

function sidebarExpanded(view: IdeSidebarActivityView): boolean {
  return shell.ideActivityView === view && !shell.ideExplorerCollapsed;
}

function itemTitle(item: (typeof items)[number]): string {
  if (item.id === 'run') {
    return ideActivityBarRunTitle(
      sidebarExpanded('run'),
      runConnectorAttention.value,
    );
  }

  if (item.id === 'team') {
    return ideActivityBarTeamTitle(
      sidebarExpanded('team'),
      shell.companyEmployeesForCurrentWorkspace,
    );
  }

  if (item.id === 'git') {
    return ideActivityBarGitTitle(sidebarExpanded('git'), dirtyFileCount.value);
  }

  if (item.id === 'search') {
    return ideActivityBarSearchTitle(sidebarExpanded('search'), searchAttentionInput.value);
  }

  if (sidebarViews.has(item.id as IdeSidebarActivityView)) {
    return ideActivityBarSidebarTitle(
      item.id as IdeSidebarActivityView,
      sidebarExpanded(item.id as IdeSidebarActivityView),
    );
  }

  if (item.id === 'agent') {
    return agentDockActivityBarTitle(agentDockState.value, agentDockExpanded.value);
  }

  if (item.id === 'terminal') {
    return ideActivityBarTerminalTitle(
      shell.workbenchTerminalPanelVisible,
      terminalRunPhase.value,
    );
  }

  return item.label;
}

function itemAriaLabel(item: (typeof items)[number]): string {
  if (item.id === 'run') {
    return ideActivityBarRunAriaLabel(
      sidebarExpanded('run'),
      runConnectorAttention.value,
    );
  }

  if (item.id === 'team') {
    return ideActivityBarTeamAriaLabel(
      sidebarExpanded('team'),
      shell.companyEmployeesForCurrentWorkspace,
    );
  }

  if (item.id === 'git') {
    return ideActivityBarGitAriaLabel(sidebarExpanded('git'), dirtyFileCount.value);
  }

  if (item.id === 'search') {
    return ideActivityBarSearchAriaLabel(sidebarExpanded('search'), searchAttentionInput.value);
  }

  if (sidebarViews.has(item.id as IdeSidebarActivityView)) {
    return ideActivityBarSidebarAriaLabel(
      item.id as IdeSidebarActivityView,
      sidebarExpanded(item.id as IdeSidebarActivityView),
    );
  }

  if (item.id === 'agent') {
    return agentDockActivityBarAriaLabel(agentDockState.value, agentDockExpanded.value);
  }

  if (item.id === 'terminal') {
    return ideActivityBarTerminalAriaLabel(
      shell.workbenchTerminalPanelVisible,
      terminalRunPhase.value,
    );
  }

  return item.label;
}

function isActive(item: (typeof items)[number]): boolean {
  if (item.id === 'agent') {
    return (
      agentDockExpanded.value ||
      (shell.ideActivityView === 'agent' && !shell.ideExplorerCollapsed)
    );
  }
  if (item.id === 'terminal') {
    return (
      shell.workbenchTerminalPanelVisible ||
      (shell.ideActivityView === 'terminal' && !shell.ideExplorerCollapsed)
    );
  }
  return shell.ideActivityView === item.id && !shell.ideExplorerCollapsed;
}

function selectView(view: IdeActivityView): void {
  const action = resolveIdeActivityBarSelectAction({
    view,
    currentView: shell.ideActivityView,
    explorerCollapsed: shell.ideExplorerCollapsed,
    agentDockCollapsed: shell.agentDockCollapsed,
    terminalPanelVisible: shell.workbenchTerminalPanelVisible,
    sidebarViews,
  });

  if (action === 'toggle-agent') {
    shell.toggleAgentDock();
    shell.focusIdeSidebarView('agent');
    return;
  }

  if (action === 'toggle-terminal') {
    shell.toggleIdeTerminalPanel();
    shell.focusIdeSidebarView('terminal');
    return;
  }

  if (action === 'toggle-explorer') {
    shell.toggleIdeExplorer();
    return;
  }

  shell.setIdeActivityView(view);
}
</script>

<template>
  <nav class="ide-activity-bar" aria-label="IDE activity bar">
    <button
      type="button"
      class="ide-activity-bar__button ide-activity-bar__button--attention"
      :class="{
        'ide-activity-bar__button--active': shell.ideAttentionPanelOpen,
        'ide-activity-bar__button--attention-hot': attentionBadgeCount > 0,
      }"
      :aria-label="attentionAriaLabel()"
      :aria-pressed="shell.ideAttentionPanelOpen"
      :title="attentionTitle()"
      @click="selectAttention"
    >
      <IdeActivityIcon name="attention" class="ide-activity-bar__icon" />
      <span
        v-if="attentionBadgeCount > 0"
        class="ide-activity-bar__badge ide-activity-bar__badge--attention"
        aria-hidden="true"
      >
        {{ attentionBadgeCount }}
      </span>
    </button>
    <button
      v-for="item in items"
      :key="item.id"
      type="button"
      class="ide-activity-bar__button"
      :class="{
        'ide-activity-bar__button--active': isActive(item),
        'ide-activity-bar__button--agent-alive':
          item.id === 'agent' &&
          agentDockAlive &&
          shell.agentDockCollapsed &&
          !agentDockEmployeeFailure &&
          !agentDockEmployeeInterrupted,
        'ide-activity-bar__button--agent-failure':
          item.id === 'agent' && agentDockEmployeeFailure && shell.agentDockCollapsed,
        'ide-activity-bar__button--agent-interrupted':
          item.id === 'agent' && agentDockEmployeeInterrupted && shell.agentDockCollapsed,
        'ide-activity-bar__button--agent-streaming':
          item.id === 'agent' && shell.agentStreamActive && shell.agentDockCollapsed,
        'ide-activity-bar__button--agent-approvals':
          item.id === 'agent' && shell.pendingApprovalsCount > 0 && shell.agentDockCollapsed,
        'ide-activity-bar__button--agent-executing':
          item.id === 'agent' &&
          shell.primaryActiveRun?.phase === 'executing' &&
          shell.agentDockCollapsed,
        'ide-activity-bar__button--agent-review-ready':
          item.id === 'agent' &&
          shell.primaryActiveRun?.phase === 'review_ready' &&
          shell.agentDockCollapsed,
        'ide-activity-bar__button--terminal-alive':
          item.id === 'terminal' && terminalAlive,
        'ide-activity-bar__button--terminal-executing':
          item.id === 'terminal' &&
          shell.primaryActiveRun?.phase === 'executing' &&
          !shell.workbenchTerminalPanelVisible,
        'ide-activity-bar__button--terminal-review-ready':
          item.id === 'terminal' &&
          shell.primaryActiveRun?.phase === 'review_ready' &&
          !shell.workbenchTerminalPanelVisible,
        'ide-activity-bar__button--run-attention':
          item.id === 'run' && runNeedsAttention,
        'ide-activity-bar__button--run-warning':
          item.id === 'run' &&
          (!watchConnected || requiredConnectorsUnavailable > 0),
        'ide-activity-bar__button--team-attention':
          item.id === 'team' && teamNeedsAttention && teamAttention.tone === 'failure',
        'ide-activity-bar__button--team-attention-interrupted':
          item.id === 'team' && teamAttention.tone === 'interrupted',
        'ide-activity-bar__button--team-attention-mixed':
          item.id === 'team' && teamAttention.tone === 'mixed',
        'ide-activity-bar__button--git-attention':
          item.id === 'git' && gitNeedsAttention,
        'ide-activity-bar__button--search-attention':
          item.id === 'search' && searchNeedsAttention,
      }"
      :aria-label="itemAriaLabel(item)"
      :title="itemTitle(item)"
      @click="selectView(item.id)"
    >
      <IdeActivityIcon :name="item.id" class="ide-activity-bar__icon" />
      <span
        v-if="item.id === 'agent' && shell.pendingApprovalsCount > 0 && shell.agentDockCollapsed"
        class="ide-activity-bar__badge"
        aria-hidden="true"
      >
        {{ shell.pendingApprovalsCount }}
      </span>
      <span
        v-else-if="item.id === 'team' && teamAttention.count > 0"
        class="ide-activity-bar__badge"
        :class="{
          'ide-activity-bar__badge--failure': teamAttention.tone === 'failure',
          'ide-activity-bar__badge--interrupted': teamAttention.tone === 'interrupted',
          'ide-activity-bar__badge--mixed': teamAttention.tone === 'mixed',
        }"
        aria-hidden="true"
      >
        {{ teamAttention.count }}
      </span>
      <span
        v-else-if="item.id === 'git' && dirtyFileCount > 0"
        class="ide-activity-bar__badge ide-activity-bar__badge--dirty"
        aria-hidden="true"
      >
        {{ dirtyFileCount }}
      </span>
      <span
        v-else-if="item.id === 'search' && searchNeedsAttention"
        class="ide-activity-bar__pulse ide-activity-bar__pulse--warning"
        aria-hidden="true"
      />
      <span
        v-else-if="item.id === 'run' && requiredConnectorsUnavailable > 0"
        class="ide-activity-bar__badge ide-activity-bar__badge--warning"
        aria-hidden="true"
      >
        {{ requiredConnectorsUnavailable }}
      </span>
      <span
        v-else-if="item.id === 'run' && !watchConnected && runNeedsAttention"
        class="ide-activity-bar__pulse ide-activity-bar__pulse--warning"
        aria-hidden="true"
      />
      <span
        v-else-if="item.id === 'run' && runNeedsAttention"
        class="ide-activity-bar__pulse ide-activity-bar__pulse--glance"
        aria-hidden="true"
      />
      <span
        v-else-if="item.id === 'agent' && agentDockEmployeeInterrupted && shell.agentDockCollapsed"
        class="ide-activity-bar__pulse ide-activity-bar__pulse--interrupted"
        aria-hidden="true"
      />
      <span
        v-else-if="item.id === 'agent' && agentDockEmployeeFailure && shell.agentDockCollapsed"
        class="ide-activity-bar__pulse ide-activity-bar__pulse--failure"
        aria-hidden="true"
      />
      <span
        v-else-if="item.id === 'agent' && agentDockAlive && shell.agentDockCollapsed"
        class="ide-activity-bar__pulse"
        aria-hidden="true"
      />
      <span
        v-else-if="item.id === 'terminal' && terminalAlive"
        class="ide-activity-bar__pulse"
        aria-hidden="true"
      />
    </button>
    <button
      type="button"
      class="ide-activity-bar__button ide-activity-bar__button--settings"
      :class="{ 'ide-activity-bar__button--active': false }"
      aria-label="Operator settings"
      title="Settings (KAIRO narration, voice, persona)"
      @click.stop="navigateToAppSurface('settings')"
    >
      <span class="ide-activity-bar__settings-icon" aria-hidden="true">⚙</span>
    </button>
  </nav>
</template>
