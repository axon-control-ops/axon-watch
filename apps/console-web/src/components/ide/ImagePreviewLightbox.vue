<script setup lang="ts">
import { computed } from 'vue';

import { useDialogAutoFocus } from '../../lib/use-dialog-auto-focus';

export type ImagePreviewLightboxItem = {
  url: string;
  filename: string;
};

const props = defineProps<{
  preview: ImagePreviewLightboxItem | null;
}>();

const emit = defineEmits<{
  close: [];
}>();

const isOpen = computed(() => props.preview !== null);
const dialogRef = useDialogAutoFocus(isOpen, {
  onEscape: () => emit('close'),
});
</script>

<template>
  <Teleport to="body">
    <div
      v-if="preview"
      ref="dialogRef"
      class="agent-dock-composer__image-lightbox"
      role="dialog"
      aria-modal="true"
      :aria-label="`Preview ${preview.filename}`"
      tabindex="-1"
      @click.self="emit('close')"
    >
      <figure class="agent-dock-composer__image-lightbox-body">
        <img
          class="agent-dock-composer__image-lightbox-img"
          :src="preview.url"
          :alt="preview.filename"
        >
        <figcaption class="agent-dock-composer__image-lightbox-caption">
          {{ preview.filename }}
        </figcaption>
      </figure>
      <button
        type="button"
        class="agent-dock-composer__image-lightbox-close"
        aria-label="Close image preview"
        @click="emit('close')"
      >
        ×
      </button>
    </div>
  </Teleport>
</template>
