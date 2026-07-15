<script setup lang="ts">
defineProps<{
  attachment: { url: string; filename: string } | null;
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
      v-if="attachment"
      class="agent-dock-composer__image-lightbox"
      role="dialog"
      aria-modal="true"
      :aria-label="`Preview ${attachment.filename}`"
      tabindex="-1"
      @click.self="emit('close')"
      @keydown="handleKeydown"
    >
      <figure class="agent-dock-composer__image-lightbox-body">
        <img
          class="agent-dock-composer__image-lightbox-img"
          :src="attachment.url"
          :alt="attachment.filename"
        >
        <figcaption class="agent-dock-composer__image-lightbox-caption">
          {{ attachment.filename }}
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
