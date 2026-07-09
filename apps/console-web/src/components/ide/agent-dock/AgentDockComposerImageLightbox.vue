<script setup lang="ts">
import type { ComposerClipboardImage } from '../../../lib/composer-clipboard-paste';

defineProps<{
  image: ComposerClipboardImage | null;
}>();

const emit = defineEmits<{
  close: [];
}>();

function handleKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    emit('close');
  }
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="image"
      class="agent-dock-composer__image-lightbox"
      role="dialog"
      aria-modal="true"
      :aria-label="`Preview ${image.name}`"
      tabindex="-1"
      @click.self="emit('close')"
      @keydown="handleKeydown"
    >
      <figure class="agent-dock-composer__image-lightbox-body">
        <img
          class="agent-dock-composer__image-lightbox-img"
          :src="image.previewUrl"
          :alt="image.name"
        >
        <figcaption class="agent-dock-composer__image-lightbox-caption">
          {{ image.name }}
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
