<script setup lang="ts">
import { ref, watch } from 'vue';

const props = defineProps<{
  title: string;
  previewUrl: string;
}>();

const loadState = ref<'loading' | 'ready' | 'error'>('loading');

watch(
  () => props.previewUrl,
  () => {
    loadState.value = props.previewUrl ? 'loading' : 'error';
  },
  { immediate: true },
);

function onFrameLoad(): void {
  loadState.value = 'ready';
}

function onFrameError(): void {
  loadState.value = 'error';
}
</script>

<template>
  <div class="editor-pdf-preview">
    <iframe
      v-if="previewUrl && loadState !== 'error'"
      class="editor-pdf-preview__frame"
      :src="previewUrl"
      :title="title"
      @load="onFrameLoad"
      @error="onFrameError"
    />
    <div v-else class="editor-pdf-preview__fallback editor-binary-preview">
      <p class="editor-binary-preview__title">{{ title }}</p>
      <p class="editor-binary-preview__body">
        {{
          loadState === 'loading'
            ? 'Loading PDF preview…'
            : 'Inline PDF preview is unavailable in this panel.'
        }}
      </p>
      <a
        v-if="previewUrl"
        class="editor-pdf-preview__open-link"
        :href="previewUrl"
        target="_blank"
        rel="noopener noreferrer"
      >
        Open PDF in browser
      </a>
    </div>
  </div>
</template>
