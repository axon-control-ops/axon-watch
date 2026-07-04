<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';

import { createMonacoEditor } from '../lib/create-monaco-editor';
import type { EditorDocumentLanguage } from '../lib/workspace-documents';

const props = defineProps<{
  title: string;
  value: string;
  language: EditorDocumentLanguage;
  description: string;
  readOnly?: boolean;
  dirty?: boolean;
}>();

const emit = defineEmits<{
  valueChange: [value: string];
  save: [];
}>();

const containerRef = ref<HTMLElement | null>(null);
const loadState = ref<'loading' | 'ready' | 'error'>('loading');
let editorController: Awaited<ReturnType<typeof createMonacoEditor>> | null = null;
let suppressChangeEmit = false;

onMounted(async () => {
  if (!containerRef.value) {
    loadState.value = 'error';
    return;
  }

  try {
    editorController = await createMonacoEditor(containerRef.value, {
      value: props.value,
      language: props.language,
      readOnly: props.readOnly,
      onValueChange: (value) => {
        if (suppressChangeEmit) {
          return;
        }
        emit('valueChange', value);
      },
    });
    loadState.value = 'ready';
  } catch {
    loadState.value = 'error';
  }
});

watch(
  () => [props.language, props.value, props.readOnly] as const,
  ([language, value, readOnly]) => {
    suppressChangeEmit = true;
    editorController?.setLanguage(language);
    editorController?.setValue(value);
    editorController?.setReadOnly(Boolean(readOnly));
    suppressChangeEmit = false;
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
      <div class="surface-host__meta-row">
        <strong>{{ props.title }}</strong>
        <span v-if="props.dirty" class="surface-host__dirty">unsaved</span>
        <button
          v-if="!props.readOnly"
          type="button"
          class="surface-host__save"
          @click="emit('save')"
        >
          Save
        </button>
      </div>
      <span>{{ props.description }}</span>
    </div>
    <div class="surface-host__body">
      <div ref="containerRef" class="surface-host__frame" aria-label="Monaco editor host" />
    </div>
  </div>
</template>
