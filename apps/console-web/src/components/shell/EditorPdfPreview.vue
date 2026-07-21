<script setup lang="ts">
defineProps<{
  title: string;
  previewUrl: string;
}>();
</script>

<template>
  <div class="editor-pdf-preview">
    <iframe
      v-if="previewUrl"
      class="editor-pdf-preview__frame"
      :src="previewUrl"
      :title="title"
    />
    <div v-else class="editor-binary-preview">
      <p class="editor-binary-preview__title">{{ title }}</p>
      <p class="editor-binary-preview__body">PDF preview unavailable.</p>
    </div>
  </div>
</template>
