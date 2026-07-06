<script setup lang="ts">
import { computed, ref } from 'vue';

import WorkspaceFileTree from '../WorkspaceFileTree.vue';
import WorkbenchIcon from '../WorkbenchIcon.vue';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const searchQuery = ref('');
const showExplorerMenu = ref(false);
const fileTreeRef = ref<InstanceType<typeof WorkspaceFileTree> | null>(null);

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

function closeExplorerMenu(): void {
  showExplorerMenu.value = false;
}

function toggleExplorerMenu(): void {
  showExplorerMenu.value = !showExplorerMenu.value;
}

function refreshExplorer(): void {
  void shell.loadWorkspaceFiles();
  closeExplorerMenu();
}

function collapseAllFolders(): void {
  fileTreeRef.value?.collapseAll();
  closeExplorerMenu();
}

function expandAllFolders(): void {
  fileTreeRef.value?.expandAll();
  closeExplorerMenu();
}

function createNewFile(): void {
  void shell.createWorkspaceFile();
}

function createNewFolder(): void {
  void shell.createWorkspaceFolder();
}
</script>

<template>
  <section
    v-if="!shell.ideExplorerCollapsed && shell.ideActivityView === 'explorer'"
    class="ide-explorer-panel hud-panel-frame"
  >
    <div class="panel-heading ide-explorer-panel__heading">
      <p class="panel-heading__title">EXPLORER</p>
      <div class="ide-explorer-panel__actions">
        <button
          type="button"
          class="ide-explorer-panel__action"
          title="New File"
          aria-label="New File"
          @click="createNewFile"
        >
          <WorkbenchIcon name="new-file" :size="13" />
        </button>
        <button
          type="button"
          class="ide-explorer-panel__action"
          title="New Folder"
          aria-label="New Folder"
          @click="createNewFolder"
        >
          <WorkbenchIcon name="folder" :size="13" />
        </button>
        <button
          type="button"
          class="ide-explorer-panel__action"
          title="Refresh Explorer"
          aria-label="Refresh Explorer"
          @click="refreshExplorer"
        >
          <span class="ide-explorer-panel__refresh" aria-hidden="true">↻</span>
        </button>
        <button
          type="button"
          class="ide-explorer-panel__action"
          title="Collapse All Folders"
          aria-label="Collapse All Folders"
          @click="collapseAllFolders"
        >
          <span class="ide-explorer-panel__collapse-all" aria-hidden="true">⊟</span>
        </button>
        <div class="ide-explorer-panel__menu-wrap">
          <button
            type="button"
            class="ide-explorer-panel__action"
            :class="{ 'ide-explorer-panel__action--active': showExplorerMenu }"
            title="Explorer options"
            aria-label="Explorer options"
            aria-haspopup="menu"
            :aria-expanded="showExplorerMenu"
            @click="toggleExplorerMenu"
          >
            <WorkbenchIcon name="more" :size="13" />
          </button>
          <div
            v-if="showExplorerMenu"
            class="ide-explorer-panel__menu"
            role="menu"
          >
            <button
              type="button"
              class="ide-explorer-panel__menu-item"
              role="menuitem"
              @click="expandAllFolders"
            >
              Expand All
            </button>
            <button
              type="button"
              class="ide-explorer-panel__menu-item"
              role="menuitem"
              @click="collapseAllFolders"
            >
              Collapse All
            </button>
            <button
              type="button"
              class="ide-explorer-panel__menu-item"
              role="menuitem"
              @click="refreshExplorer"
            >
              Refresh Explorer
            </button>
          </div>
        </div>
        <button
          type="button"
          class="panel-heading__action ide-explorer-panel__collapse"
          aria-label="Collapse explorer panel"
          title="Collapse explorer panel"
          @click="shell.toggleIdeExplorer()"
        >
          ‹
        </button>
      </div>
    </div>
    <div class="ide-explorer-panel__body">
      <WorkspaceFileTree
        ref="fileTreeRef"
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
    <div class="panel-heading ide-explorer-panel__heading">
      <p class="panel-heading__title">SEARCH</p>
      <button
        type="button"
        class="panel-heading__action ide-explorer-panel__collapse"
        aria-label="Collapse panel"
        @click="shell.toggleIdeExplorer()"
      >
        ‹
      </button>
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
    <div class="panel-heading ide-explorer-panel__heading">
      <p class="panel-heading__title">SOURCE CONTROL</p>
      <button
        type="button"
        class="panel-heading__action ide-explorer-panel__collapse"
        aria-label="Collapse panel"
        @click="shell.toggleIdeExplorer()"
      >
        ‹
      </button>
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
    <div class="panel-heading ide-explorer-panel__heading">
      <p class="panel-heading__title">RUN</p>
      <button
        type="button"
        class="panel-heading__action ide-explorer-panel__collapse"
        aria-label="Collapse panel"
        @click="shell.toggleIdeExplorer()"
      >
        ‹
      </button>
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
    <div class="panel-heading ide-explorer-panel__heading">
      <p class="panel-heading__title">AGENT</p>
      <button
        type="button"
        class="panel-heading__action ide-explorer-panel__collapse"
        aria-label="Collapse panel"
        @click="shell.toggleIdeExplorer()"
      >
        ‹
      </button>
    </div>
    <p class="region-copy ide-explorer-panel__stub-copy">
      Agent dock stays pinned on the right. Use Ctrl/Cmd+\ to collapse or expand it.
    </p>
  </section>

  <section
    v-else-if="!shell.ideExplorerCollapsed"
    class="ide-explorer-panel ide-explorer-panel--stub hud-panel-frame"
  >
    <div class="panel-heading ide-explorer-panel__heading">
      <p class="panel-heading__title">TERMINAL</p>
      <button
        type="button"
        class="panel-heading__action ide-explorer-panel__collapse"
        aria-label="Collapse panel"
        @click="shell.toggleIdeExplorer()"
      >
        ‹
      </button>
    </div>
    <p class="region-copy ide-explorer-panel__stub-copy">
      Terminal lives in the center bottom panel. Use Ctrl/Cmd+J to show or hide it.
    </p>
  </section>
</template>
