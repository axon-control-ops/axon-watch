<script setup lang="ts">
import { computed } from 'vue';

import { normalizeGeneratedImagePath, resolveThreadImageUrl } from '../../lib/thread-image-url';
import { useShellStore } from '../../stores/shell';

const props = defineProps<{
  path: string;
  open?: boolean;
}>();

const shell = useShellStore();

const imageUrl = computed(() =>
  resolveThreadImageUrl(props.path, {
    workspaceId: shell.currentWorkspace?.workspace_id ?? null,
  }),
);

const resolvedPath = computed(() => normalizeGeneratedImagePath(props.path));

const fileName = computed(() => resolvedPath.value.split('/').pop() || resolvedPath.value);

function openInCanvas(): void {
  void shell.openWorkspaceFile(resolvedPath.value);
}
</script>

<template>
  <figure class="agent-block agent-block--image conversation-seam__inline-image">
    <button
      type="button"
      class="conversation-seam__inline-image-button"
      :title="`Open ${path} in canvas`"
      @click="openInCanvas"
    >
      <img
        class="conversation-seam__inline-image-preview"
        :src="imageUrl"
        :alt="fileName"
        loading="lazy"
      >
    </button>
    <figcaption class="conversation-seam__inline-image-caption">
      <button type="button" class="conversation-seam__inline-image-link" @click="openInCanvas">
        {{ fileName }}
      </button>
      <span v-if="open" class="conversation-seam__inline-image-live" aria-hidden="true">generating…</span>
    </figcaption>
  </figure>
</template>
