<script setup lang="ts">
import { computed, ref } from 'vue';

import { normalizeEditedFilePath } from '../../lib/agent-transcript-blocks';
import { useShellStore } from '../../stores/shell';

const props = defineProps<{
  path: string;
  reason: string;
}>();

const shell = useShellStore();
const expanded = ref(false);

const normalizedPath = computed(() => normalizeEditedFilePath(props.path));
const shortReason = computed(() => {
  const flattened = props.reason.replace(/\s+/g, ' ').trim();
  if (flattened.length <= 160) {
    return flattened;
  }
  return `${flattened.slice(0, 157).trimEnd()}…`;
});

function openPath(): void {
  if (!normalizedPath.value) {
    return;
  }
  shell.openWorkspaceFile(normalizedPath.value);
}
</script>

<template>
  <div class="agent-block agent-block--edit-failed">
    <div class="agent-block__edit-failed-header">
      <span class="agent-block__edit-failed-badge" aria-hidden="true">Edit failed</span>
      <button
        v-if="normalizedPath"
        type="button"
        class="agent-block__edit-failed-path"
        :title="`Open ${normalizedPath}`"
        @click="openPath"
      >
        {{ normalizedPath }}
      </button>
      <span v-else class="agent-block__edit-failed-path agent-block__edit-failed-path--static">
        unknown file
      </span>
    </div>
    <p class="agent-block__edit-failed-reason">
      {{ expanded ? reason : shortReason }}
    </p>
    <button
      v-if="reason.replace(/\s+/g, ' ').trim().length > 160"
      type="button"
      class="agent-block__edit-failed-toggle"
      @click="expanded = !expanded"
    >
      {{ expanded ? 'Show less' : 'Show more' }}
    </button>
  </div>
</template>
