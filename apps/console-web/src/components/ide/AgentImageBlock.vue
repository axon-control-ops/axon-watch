<script setup lang="ts">
import { computed, ref } from 'vue';

import {
  normalizeGeneratedImagePath,
  resolveThreadImageUrl,
} from '../../lib/thread-image-url';
import { useShellStore } from '../../stores/shell';

const props = defineProps<{
  path: string;
  open?: boolean;
  attachmentUrl?: string | null;
}>();

const shell = useShellStore();
const enlarged = ref(false);

const resolvedPath = computed(() => normalizeGeneratedImagePath(props.path));

const fileName = computed(() => resolvedPath.value.split('/').pop() || resolvedPath.value);

const imageUrl = computed(() =>
  resolveThreadImageUrl(props.path, {
    workspaceId: shell.currentWorkspace?.workspace_id ?? null,
    attachmentUrl: props.attachmentUrl,
  }),
);

function openLightbox(): void {
  if (!imageUrl.value) {
    return;
  }
  enlarged.value = true;
}

function closeLightbox(): void {
  enlarged.value = false;
}

function handleLightboxKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    closeLightbox();
  }
}

function openInCanvas(): void {
  void shell.openWorkspaceFile(resolvedPath.value);
}
</script>

<template>
  <figure class="agent-block agent-block--image conversation-seam__inline-image">
    <button
      type="button"
      class="conversation-seam__inline-image-button"
      :title="`Preview ${fileName}`"
      @click="openLightbox"
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
        Open in canvas
      </button>
      <span class="conversation-seam__inline-image-caption-name">{{ fileName }}</span>
      <span v-if="open" class="conversation-seam__inline-image-live" aria-hidden="true">generating…</span>
    </figcaption>
  </figure>

  <Teleport to="body">
    <div
      v-if="enlarged"
      class="agent-dock-composer__image-lightbox"
      role="dialog"
      aria-modal="true"
      :aria-label="`Preview ${fileName}`"
      tabindex="-1"
      @click.self="closeLightbox"
      @keydown="handleLightboxKeydown"
    >
      <figure class="agent-dock-composer__image-lightbox-body">
        <img
          class="agent-dock-composer__image-lightbox-img"
          :src="imageUrl"
          :alt="fileName"
        >
        <figcaption class="agent-dock-composer__image-lightbox-caption">
          {{ fileName }}
        </figcaption>
      </figure>
      <button
        type="button"
        class="agent-dock-composer__image-lightbox-close"
        aria-label="Close image preview"
        @click="closeLightbox"
      >
        ×
      </button>
    </div>
  </Teleport>
</template>
