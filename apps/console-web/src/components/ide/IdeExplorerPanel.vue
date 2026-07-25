<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue';

import WorkspaceFileTree from '../WorkspaceFileTree.vue';
import WorkbenchIcon from '../WorkbenchIcon.vue';
import IdeExplorerActivityPanels from './IdeExplorerActivityPanels.vue';
import { ensureWorkspaceFilesLoaded } from '../../composables/useIdeEditorStatusBar';
import { ideActivityPanelCollapseAriaLabel } from '../../lib/ide-activity-panel-view';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const showExplorerMenu = ref(false);
const explorerMenuWrapRef = ref<HTMLElement | null>(null);
const fileTreeRef = ref<InstanceType<typeof WorkspaceFileTree> | null>(null);

function closeExplorerMenu(): void {
  showExplorerMenu.value = false;
}

function handleExplorerMenuPointerDown(event: MouseEvent): void {
  if (!showExplorerMenu.value) {
    return;
  }

  const target = event.target;
  if (!(target instanceof Node)) {
    return;
  }

  if (!explorerMenuWrapRef.value?.contains(target)) {
    closeExplorerMenu();
  }
}

function handleExplorerMenuKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    closeExplorerMenu();
  }
}

onMounted(() => {
  document.addEventListener('mousedown', handleExplorerMenuPointerDown);
  document.addEventListener('keydown', handleExplorerMenuKeydown);
});

onUnmounted(() => {
  document.removeEventListener('mousedown', handleExplorerMenuPointerDown);
  document.removeEventListener('keydown', handleExplorerMenuKeydown);
});

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
  closeExplorerMenu();
  fileTreeRef.value?.beginInlineCreate?.('file');
}

function createNewFolder(): void {
  closeExplorerMenu();
  fileTreeRef.value?.beginInlineCreate?.('folder');
}

function handleCreateFile(path: string): void {
  void shell.createWorkspaceFile(path);
}

function handleCreateFolder(path: string): void {
  void shell.createWorkspaceFolder(path);
}

watch(
  () => shell.ideActivityView === 'explorer' && !shell.ideExplorerCollapsed,
  (active) => {
    if (active) {
      ensureWorkspaceFilesLoaded(shell);
    }
  },
  { immediate: true },
);
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
          <WorkbenchIcon name="new-file" :size="16" />
        </button>
        <button
          type="button"
          class="ide-explorer-panel__action"
          title="New Folder"
          aria-label="New Folder"
          @click="createNewFolder"
        >
          <WorkbenchIcon name="new-folder" :size="16" />
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
        <div ref="explorerMenuWrapRef" class="ide-explorer-panel__menu-wrap">
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
            <WorkbenchIcon name="more" :size="16" />
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
              @click="createNewFile"
            >
              New File
            </button>
            <button
              type="button"
              class="ide-explorer-panel__menu-item"
              role="menuitem"
              @click="createNewFolder"
            >
              New Folder
            </button>
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
          :aria-label="ideActivityPanelCollapseAriaLabel('explorer')"
          :title="ideActivityPanelCollapseAriaLabel('explorer')"
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
        @create-file="handleCreateFile"
        @create-folder="handleCreateFolder"
      />
    </div>
  </section>

  <IdeExplorerActivityPanels
    v-else-if="!shell.ideExplorerCollapsed"
  />
</template>
