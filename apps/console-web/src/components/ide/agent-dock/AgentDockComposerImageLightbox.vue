<script setup lang="ts">
import { computed } from 'vue';

import type { ComposerClipboardImage } from '../../../lib/composer-clipboard-paste';
import ImagePreviewLightbox from '../ImagePreviewLightbox.vue';

const props = defineProps<{
  image: ComposerClipboardImage | null;
}>();

const emit = defineEmits<{
  close: [];
}>();

const preview = computed(() =>
  props.image
    ? {
        url: props.image.previewUrl,
        filename: props.image.name,
      }
    : null,
);
</script>

<template>
  <ImagePreviewLightbox
    :preview="preview"
    @close="emit('close')"
  />
</template>
