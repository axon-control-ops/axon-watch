<script setup lang="ts">
import WorkspaceFileTree from '../WorkspaceFileTree.vue';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
</script>

<template>
  <section
    v-if="!shell.ideExplorerCollapsed && shell.ideActivityView === 'explorer'"
    class="ide-explorer-panel hud-panel-frame"
  >
    <div class="panel-heading">
      <p class="panel-heading__title">EXPLORER</p>
      <button
        type="button"
        class="panel-heading__action"
        aria-label="Collapse explorer"
        @click="shell.toggleIdeExplorer()"
      >
        ‹
      </button>
    </div>
    <div class="ide-explorer-panel__body">
      <WorkspaceFileTree
        :entries="shell.workspaceFileEntries"
        :active-path="shell.activeWorkspaceFilePath"
        :load-state="shell.workspaceFilesLoadState"
        :error="shell.workspaceFilesError"
        @open="shell.openWorkspaceFile"
      />
    </div>
  </section>

  <section
    v-else-if="!shell.ideExplorerCollapsed && shell.ideActivityView !== 'explorer'"
    class="ide-explorer-panel ide-explorer-panel--stub hud-panel-frame"
  >
    <div class="panel-heading">
      <p class="panel-heading__title">{{ shell.ideActivityView.toUpperCase() }}</p>
    </div>
    <p class="region-copy ide-explorer-panel__stub-copy">
      {{ shell.ideActivityView === 'search' ? 'Search panel coming soon.' : 'Panel stub.' }}
    </p>
  </section>
</template>
