<script setup lang="ts">
import { computed, ref } from 'vue';

import {
  normalizeGeneratedImagePath,
  resolveThreadImageUrl,
} from '../../lib/thread-image-url';
import { useShellStore } from '../../stores/shell';
import ImagePreviewLightbox from './ImagePreviewLightbox.vue';

const props = defineProps<{
  path: string;
  open?: boolean;
  attachmentUrl?: string | null;
}>();

const shell = useShellStore();
const enlarged = ref(false);

const projectRoot = computed(() => shell.currentWorkspace?.project_root ?? null);

const resolvedPath = computed(() =>
  normalizeGeneratedImagePath(props.path, projectRoot.value),
);

const fileName = computed(() => resolvedPath.value.split('/').pop() || resolvedPath.value);

const imageUrl = computed(() =>
  resolveThreadImageUrl(props.path, {
    workspaceId: shell.currentWorkspace?.workspace_id ?? null,
    projectRoot: projectRoot.value,
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

const enlargedPreview = computed(() => {
  if (!enlarged.value || !imageUrl.value) {
    return null;
  }
  return {
    url: imageUrl.value,
    filename: fileName.value,
  };
});

function openInCanvas(): void {
  const url = imageUrl.value.trim();
  const attachmentUrl =
    String(props.attachmentUrl ?? '').trim() ||
    (url.includes('/api/chat/attachments/') ? url : '');
  void shell.openImageInCanvas({
    path: props.path,
    attachmentUrl: attachmentUrl || null,
  });
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

  <ImagePreviewLightbox
    :preview="enlargedPreview"
    @close="closeLightbox"
  />
</template>
