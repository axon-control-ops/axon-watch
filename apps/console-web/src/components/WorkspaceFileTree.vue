<script setup lang="ts">
import { computed, ref } from 'vue';

import {
  buildWorkspaceFileTree,
  flattenWorkspaceFileTree,
} from '../lib/workspace-file-tree';

const props = defineProps<{
  entries: Array<{ path: string; size_bytes: number }>;
  activePath: string | null;
  loadState: 'idle' | 'loading' | 'loaded' | 'error';
  error: string | null;
}>();

const emit = defineEmits<{
  open: [path: string];
}>();

const expandedDirectories = ref<Record<string, boolean>>({});

const rows = computed(() =>
  flattenWorkspaceFileTree(buildWorkspaceFileTree(props.entries), expandedDirectories.value),
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
</script>

<template>
  <div class="workspace-file-tree">
    <p v-if="loadState === 'loading'" class="region-copy">Loading workspace files…</p>
    <p v-else-if="loadState === 'error'" class="region-copy">{{ error }}</p>
    <p v-else-if="entries.length === 0" class="region-copy">No workspace files found.</p>

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
            {{ isExpanded(row.path) ? '▾' : '▸' }}
          </span>
          <span>{{ row.name }}</span>
        </button>
      </li>
    </ul>
  </div>
</template>
