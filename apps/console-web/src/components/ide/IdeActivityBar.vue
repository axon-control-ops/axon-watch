<script setup lang="ts">
import { computed } from 'vue';

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
  ideActivityBarRunAriaLabel,
  ideActivityBarRunNeedsAttention,
  ideActivityBarRunTitle,
  ideActivityBarSidebarAriaLabel,
  ideActivityBarSidebarTitle,
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

const items: Array<{ id: IdeActivityView; label: string }> = [
  { id: 'explorer', label: 'Explorer' },
  { id: 'search', label: 'Search' },
  { id: 'git', label: 'Source Control' },
  { id: 'run', label: 'Run' },
  { id: 'team', label: 'Team' },
  { id: 'terminal', label: 'Terminal' },
  { id: 'agent', label: 'Agent Dock' },
];

const agentDockExpanded = computed(() => !shell.agentDockCollapsed);

const agentDockState = computed(() => ({
  streaming: shell.agentStreamActive,
  pendingApprovals: shell.pendingApprovalsCount,
  runPhase: shell.primaryActiveRun?.phase ?? null,
  employeeFailureLine: shell.activeIdeEmployeeFailureLine,
  employeeShiftInterrupted: shell.activeIdeEmployeeShiftInterrupted,
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
