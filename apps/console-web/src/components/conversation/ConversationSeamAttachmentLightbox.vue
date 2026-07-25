<script setup lang="ts">
import ImagePreviewLightbox from '../ide/ImagePreviewLightbox.vue';

defineProps<{
  attachment: { url: string; filename: string } | null;
}>();

const emit = defineEmits<{
  close: [];
}>();
</script>

<template>
  <ImagePreviewLightbox
    :preview="attachment"
    @close="emit('close')"
  />
</template>
