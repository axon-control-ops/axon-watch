<script setup lang="ts">
import type { IdeActivityView } from '../../lib/ide-layout-prefs';
import IdeActivityIcon from './IdeActivityIcon.vue';
import { navigateToAppSurface } from '../../lib/app-surface-route';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

const items: Array<{ id: IdeActivityView; label: string; title: string }> = [
  { id: 'explorer', label: 'Explorer', title: 'Explorer (Ctrl/Cmd+B)' },
  { id: 'search', label: 'Search', title: 'Search' },
  { id: 'git', label: 'Source Control', title: 'Source Control' },
  { id: 'run', label: 'Run', title: 'Run' },
  { id: 'team', label: 'Team', title: 'Workspace team' },
  { id: 'terminal', label: 'Terminal', title: 'Terminal (Ctrl/Cmd+J)' },
  { id: 'agent', label: 'Agent Dock', title: 'Agent dock (Ctrl/Cmd+\\)' },
];

function isActive(item: (typeof items)[number]): boolean {
  if (item.id === 'agent') {
    return !shell.agentDockCollapsed;
  }
  if (item.id === 'terminal') {
    return shell.ideActivityView === 'terminal';
  }
  return shell.ideActivityView === item.id && !shell.ideExplorerCollapsed;
}

function selectView(view: IdeActivityView): void {
  if (
    view === 'explorer' &&
    shell.ideActivityView === 'explorer' &&
    !shell.ideExplorerCollapsed
  ) {
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
      :class="{ 'ide-activity-bar__button--active': isActive(item) }"
      :aria-label="item.label"
      :title="item.title"
      @click="selectView(item.id)"
    >
      <IdeActivityIcon :name="item.id" class="ide-activity-bar__icon" />
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
