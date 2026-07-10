<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';

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
  createFile: [path: string];
  createFolder: [path: string];
}>();

type InlineCreateKind = 'file' | 'folder';

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

const inlineCreate = ref<{
  kind: InlineCreateKind;
  parentPath: string;
  depth: number;
  name: string;
} | null>(null);
const inlineInputRef = ref<HTMLInputElement | null>(null);
const inlineError = ref<string | null>(null);

watch(
  () => inlineCreate.value,
  async (value) => {
    if (!value) {
      return;
    }
    await nextTick();
    inlineInputRef.value?.focus();
    inlineInputRef.value?.select();
  },
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

function parentDirectoryForCreate(): { parentPath: string; depth: number } {
  if (props.activePath) {
    const parts = props.activePath.split('/').filter(Boolean);
    if (parts.length > 1) {
      const parentPath = parts.slice(0, -1).join('/');
      return { parentPath, depth: parts.length - 1 };
    }
  }
  return { parentPath: '', depth: 0 };
}

function beginInlineCreate(kind: InlineCreateKind, parentPath = ''): void {
  const resolvedParent = parentPath || parentDirectoryForCreate().parentPath;
  const depth = resolvedParent ? resolvedParent.split('/').filter(Boolean).length : 0;
  if (resolvedParent) {
    const nextExpanded = { ...expandedDirectories.value };
    const segments = resolvedParent.split('/').filter(Boolean);
    for (let index = 1; index <= segments.length; index += 1) {
      nextExpanded[segments.slice(0, index).join('/')] = true;
    }
    expandedDirectories.value = nextExpanded;
  }
  inlineError.value = null;
  inlineCreate.value = {
    kind,
    parentPath: resolvedParent,
    depth,
    name: kind === 'file' ? 'untitled.ts' : 'new-folder',
  };
}

function cancelInlineCreate(): void {
  inlineCreate.value = null;
  inlineError.value = null;
}

function commitInlineCreate(): void {
  const draft = inlineCreate.value;
  if (!draft) {
    return;
  }
  const name = draft.name.trim().replace(/^\/+|\/+$/g, '');
  if (!name || name.includes('..') || name.includes('/')) {
    inlineError.value = 'Enter a single path segment (no / or ..).';
    return;
  }
  const fullPath = draft.parentPath ? `${draft.parentPath}/${name}` : name;
  if (draft.kind === 'file') {
    emit('createFile', fullPath);
  } else {
    emit('createFolder', fullPath);
  }
  cancelInlineCreate();
}

function handleInlineKeydown(event: KeyboardEvent): void {
  if (event.key === 'Enter') {
    event.preventDefault();
    commitInlineCreate();
  } else if (event.key === 'Escape') {
    event.preventDefault();
    cancelInlineCreate();
  }
}

defineExpose({
  expandAll,
  collapseAll,
  beginInlineCreate,
  cancelInlineCreate,
});
</script>

<template>
  <div class="workspace-file-tree">
    <p v-if="statusMessage" class="region-copy workspace-file-tree__status">{{ statusMessage }}</p>

    <ul v-if="!statusMessage || inlineCreate" class="workspace-file-tree__list">
      <li
        v-if="inlineCreate && !inlineCreate.parentPath"
        class="workspace-file-tree__item workspace-file-tree__item--inline"
      >
        <div
          class="workspace-file-tree__row workspace-file-tree__row--inline"
          :style="{ paddingLeft: '6px' }"
        >
          <WorkbenchIcon
            :name="inlineCreate.kind === 'folder' ? 'folder' : 'file'"
            :size="16"
            class="workspace-file-tree__file-icon"
          />
          <input
            ref="inlineInputRef"
            v-model="inlineCreate.name"
            class="workspace-file-tree__inline-input"
            :aria-label="inlineCreate.kind === 'folder' ? 'New folder name' : 'New file name'"
            @keydown="handleInlineKeydown"
            @blur="commitInlineCreate"
          />
        </div>
        <p v-if="inlineError" class="workspace-file-tree__inline-error">{{ inlineError }}</p>
      </li>

      <template v-for="row in rows" :key="`${row.kind}:${row.path}`">
        <li class="workspace-file-tree__item">
          <button
            type="button"
            class="workspace-file-tree__row"
            :class="{
              'workspace-file-tree__row--directory': row.kind === 'directory',
              'workspace-file-tree__row--file': row.kind === 'file',
              'workspace-file-tree__row--active': row.kind === 'file' && activePath === row.path,
            }"
            :style="{ paddingLeft: `${6 + row.depth * 8}px` }"
            @click="handleRowClick(row)"
          >
            <span v-if="row.kind === 'directory'" class="workspace-file-tree__chevron">
              <WorkbenchIcon
                :name="isExpanded(row.path) ? 'folder-open' : 'folder'"
                :size="16"
              />
            </span>
            <WorkbenchIcon v-else name="file" :size="16" class="workspace-file-tree__file-icon" />
            <span>{{ row.name }}</span>
          </button>
        </li>

        <li
          v-if="inlineCreate && inlineCreate.parentPath === row.path && row.kind === 'directory' && isExpanded(row.path)"
          class="workspace-file-tree__item workspace-file-tree__item--inline"
        >
          <div
            class="workspace-file-tree__row workspace-file-tree__row--inline"
            :style="{ paddingLeft: `${6 + (row.depth + 1) * 8}px` }"
          >
            <WorkbenchIcon
              :name="inlineCreate.kind === 'folder' ? 'folder' : 'file'"
              :size="16"
              class="workspace-file-tree__file-icon"
            />
            <input
              ref="inlineInputRef"
              v-model="inlineCreate.name"
              class="workspace-file-tree__inline-input"
              :aria-label="inlineCreate.kind === 'folder' ? 'New folder name' : 'New file name'"
              @keydown="handleInlineKeydown"
              @blur="commitInlineCreate"
            />
          </div>
          <p v-if="inlineError" class="workspace-file-tree__inline-error">{{ inlineError }}</p>
        </li>
      </template>
    </ul>
  </div>
</template>

<style scoped>
.workspace-file-tree__row--inline {
  display: flex;
  align-items: center;
  gap: 0.28rem;
  min-height: 1.45rem;
}

.workspace-file-tree__inline-input {
  flex: 1;
  min-width: 0;
  border: 1px solid rgba(0, 210, 255, 0.45);
  border-radius: 0.2rem;
  background: rgba(4, 14, 22, 0.95);
  color: rgba(230, 242, 255, 0.96);
  font: inherit;
  font-size: 0.72rem;
  line-height: 1.2;
  padding: 0.08rem 0.28rem;
  outline: none;
}

.workspace-file-tree__inline-input:focus {
  border-color: rgba(0, 242, 255, 0.75);
  box-shadow: 0 0 0 1px rgba(0, 210, 255, 0.2);
}

.workspace-file-tree__inline-error {
  margin: 0.1rem 0 0.25rem;
  padding-left: 1.6rem;
  font-size: 0.62rem;
  color: rgba(255, 150, 150, 0.92);
}
</style>
