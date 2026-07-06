<script setup lang="ts">
import { computed, ref } from 'vue';

import WorkspaceFileTree from '../WorkspaceFileTree.vue';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const searchQuery = ref('');

const searchResults = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();
  if (!query) {
    return shell.workspaceFileEntries.slice(0, 24);
  }
  return shell.workspaceFileEntries
    .filter((entry) => entry.path.toLowerCase().includes(query))
    .slice(0, 32);
});

const dirtyDocuments = computed(() =>
  shell.editorDocuments.filter((document) => document.source === 'file' && document.dirty),
);

function openSearchResult(path: string): void {
  void shell.openWorkspaceFile(path);
}
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
        :has-workspace="Boolean(shell.currentWorkspace?.workspace_id)"
        @open="shell.openWorkspaceFile"
      />
    </div>
  </section>

  <section
    v-else-if="!shell.ideExplorerCollapsed && shell.ideActivityView === 'search'"
    class="ide-explorer-panel ide-explorer-panel--stub hud-panel-frame"
  >
    <div class="panel-heading">
      <p class="panel-heading__title">SEARCH</p>
    </div>
    <div class="ide-panel-search">
      <input
        v-model="searchQuery"
        class="ide-panel-search__input"
        type="search"
        placeholder="Search file paths..."
      />
      <ul class="ide-panel-list">
        <li v-for="entry in searchResults" :key="entry.path">
          <button type="button" class="ide-panel-list__button" @click="openSearchResult(entry.path)">
            {{ entry.path }}
          </button>
        </li>
      </ul>
    </div>
  </section>

  <section
    v-else-if="!shell.ideExplorerCollapsed && shell.ideActivityView === 'git'"
    class="ide-explorer-panel ide-explorer-panel--stub hud-panel-frame"
  >
    <div class="panel-heading">
      <p class="panel-heading__title">SOURCE CONTROL</p>
    </div>
    <div class="ide-panel-search">
      <p class="region-copy ide-panel-caption">
        {{ dirtyDocuments.length ? `${dirtyDocuments.length} file(s) with unsaved changes` : 'No unsaved files in the current workspace.' }}
      </p>
      <ul v-if="dirtyDocuments.length" class="ide-panel-list">
        <li v-for="document in dirtyDocuments" :key="document.id">
          <button type="button" class="ide-panel-list__button" @click="shell.setActiveEditorDocument(document.id)">
            {{ document.title }}
          </button>
        </li>
      </ul>
    </div>
  </section>

  <section
    v-else-if="!shell.ideExplorerCollapsed && shell.ideActivityView === 'run'"
    class="ide-explorer-panel ide-explorer-panel--stub hud-panel-frame"
  >
    <div class="panel-heading">
      <p class="panel-heading__title">RUN</p>
    </div>
    <div class="ide-panel-search">
      <p class="region-copy ide-panel-caption">
        {{ shell.primaryActiveRun ? `${shell.primaryActiveRun.run_id} · ${shell.primaryActiveRun.phase}` : 'No active run' }}
      </p>
      <p v-if="shell.primaryActiveRun" class="region-copy ide-panel-caption">
        {{ shell.primaryActiveRun.summary }}
      </p>
      <button
        v-if="shell.primaryActiveRun && (shell.canStopPrimaryRun || shell.primaryActiveRun.phase === 'executing')"
        type="button"
        class="ide-panel-action"
        :disabled="!shell.canStopPrimaryRun && shell.primaryActiveRun.phase !== 'executing'"
        @click="shell.stopPrimaryRun()"
      >
        {{ shell.runMutationState === 'stopping' ? 'STOPPING…' : 'STOP RUN' }}
      </button>
    </div>
  </section>

  <section
    v-else-if="!shell.ideExplorerCollapsed && shell.ideActivityView === 'agent'"
    class="ide-explorer-panel ide-explorer-panel--stub hud-panel-frame"
  >
    <div class="panel-heading">
      <p class="panel-heading__title">AGENT</p>
    </div>
    <p class="region-copy ide-explorer-panel__stub-copy">
      Agent dock stays pinned on the right. Use Ctrl/Cmd+\ to collapse or expand it.
    </p>
  </section>

  <section
    v-else-if="!shell.ideExplorerCollapsed"
    class="ide-explorer-panel ide-explorer-panel--stub hud-panel-frame"
  >
    <div class="panel-heading">
      <p class="panel-heading__title">TERMINAL</p>
    </div>
    <p class="region-copy ide-explorer-panel__stub-copy">
      Terminal lives in the center bottom panel. Use Ctrl/Cmd+J to show or hide it.
    </p>
  </section>
</template>
