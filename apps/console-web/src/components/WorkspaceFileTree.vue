<script setup lang="ts">
import { computed, ref } from 'vue';

import WorkbenchIcon from './WorkbenchIcon.vue';
import {
  buildWorkspaceFileTree,
  buildCollapsedDirectoryState,
  buildExpandedDirectoryState,
  flattenWorkspaceFileTree,
} from '../lib/workspace-file-tree';
import { workspaceExplorerStatusMessage } from '../lib/workspace-explorer-view';

const props = defineProps<{
  entries: Array<{ path: string; size_bytes: number }>;
  activePath: string | null;
  loadState: 'idle' | 'loading' | 'loaded' | 'error';
  error: string | null;
  hasWorkspace?: boolean;
}>();

const emit = defineEmits<{
  open: [path: string];
}>();

const expandedDirectories = ref<Record<string, boolean>>({});
const treeNodes = computed(() => buildWorkspaceFileTree(props.entries));

const rows = computed(() =>
  flattenWorkspaceFileTree(treeNodes.value, expandedDirectories.value),
);

const statusMessage = computed(() =>
  workspaceExplorerStatusMessage({
    loadState: props.loadState,
    hasWorkspace: props.hasWorkspace ?? true,
    entryCount: props.entries.length,
    error: props.error,
  }),
);

function toggleDirectory(path: string): void {
  expandedDirectories.value = {
    ...expandedDirectories.value,
    [path]: !(expandedDirectories.value[path] ?? true),
  };
}

function isExpanded(path: string): boolean {
  return expandedDirectories.value[path] ?? true;
}

function handleRowClick(row: { path: string; kind: 'file' | 'directory' }): void {
  if (row.kind === 'directory') {
    toggleDirectory(row.path);
    return;
  }

  emit('open', row.path);
}

function expandAll(): void {
  expandedDirectories.value = buildExpandedDirectoryState(treeNodes.value);
}

function collapseAll(): void {
  expandedDirectories.value = buildCollapsedDirectoryState(treeNodes.value);
}

defineExpose({
  expandAll,
  collapseAll,
});
</script>

<template>
  <div class="workspace-file-tree">
    <p v-if="statusMessage" class="region-copy workspace-file-tree__status">{{ statusMessage }}</p>

    <ul v-else class="workspace-file-tree__list">
      <li v-for="row in rows" :key="`${row.kind}:${row.path}`" class="workspace-file-tree__item">
        <button
          type="button"
          class="workspace-file-tree__row"
          :class="{
            'workspace-file-tree__row--directory': row.kind === 'directory',
            'workspace-file-tree__row--file': row.kind === 'file',
            'workspace-file-tree__row--active': row.kind === 'file' && activePath === row.path,
          }"
          :style="{ paddingLeft: `${0.35 + row.depth * 0.75}rem` }"
          @click="handleRowClick(row)"
        >
          <span v-if="row.kind === 'directory'" class="workspace-file-tree__chevron">
            <WorkbenchIcon
              :name="isExpanded(row.path) ? 'folder-open' : 'folder'"
              :size="13"
            />
          </span>
          <WorkbenchIcon v-else name="file" :size="13" class="workspace-file-tree__file-icon" />
          <span>{{ row.name }}</span>
        </button>
      </li>
    </ul>
  </div>
</template>
