<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';

import { createMonacoEditor } from '../lib/create-monaco-editor';

const props = defineProps<{
  title: string;
  value: string;
  language: 'markdown' | 'json';
  description: string;
}>();

const containerRef = ref<HTMLElement | null>(null);
const loadState = ref<'loading' | 'ready' | 'error'>('loading');
let editorController: Awaited<ReturnType<typeof createMonacoEditor>> | null = null;

onMounted(async () => {
  if (!containerRef.value) {
    loadState.value = 'error';
    return;
  }

  try {
    editorController = await createMonacoEditor(containerRef.value, {
      value: props.value,
      language: props.language,
    });
    loadState.value = 'ready';
  } catch {
    loadState.value = 'error';
  }
});

watch(
  () => [props.language, props.value] as const,
  ([language, value]) => {
    editorController?.setLanguage(language);
    editorController?.setValue(value);
  },
);

onBeforeUnmount(() => {
  editorController?.dispose();
  editorController = null;
});
</script>

<template>
  <div class="surface-host">
    <p v-if="loadState === 'loading'" class="surface-host__status">Loading Monaco editor…</p>
    <p v-else-if="loadState === 'error'" class="surface-host__status">Editor host unavailable</p>
    <div class="surface-host__meta">
      <strong>{{ props.title }}</strong>
      <span>{{ props.description }}</span>
    </div>
    <div class="surface-host__body">
      <div ref="containerRef" class="surface-host__frame" aria-label="Monaco editor host" />
    </div>
  </div>
</template>
