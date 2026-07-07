<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';

import { createMonacoEditor } from '../lib/create-monaco-editor';
import type { EditorDocumentLanguage } from '../lib/workspace-documents';
import type { EditorSelectionSnapshot } from '../lib/create-monaco-editor';

const props = defineProps<{
  title: string;
  value: string;
  language: EditorDocumentLanguage;
  description: string;
  readOnly?: boolean;
  dirty?: boolean;
  variant?: 'default' | 'mockup';
}>();

const emit = defineEmits<{
  valueChange: [value: string];
  save: [];
  cursorChange: [position: { line: number; column: number }];
  selectionChange: [selection: EditorSelectionSnapshot | null];
}>();

const containerRef = ref<HTMLElement | null>(null);
const loadState = ref<'loading' | 'ready' | 'error'>('loading');
let editorController: Awaited<ReturnType<typeof createMonacoEditor>> | null = null;
let suppressChangeEmit = false;

function focusEditor(): void {
  editorController?.focus();
}

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
      variant: props.variant,
      onValueChange: (value) => {
        if (suppressChangeEmit) {
          return;
        }
        emit('valueChange', value);
      },
      onCursorChange: (position) => {
        emit('cursorChange', position);
      },
      onSelectionChange: (selection) => {
        emit('selectionChange', selection);
      },
    });
    loadState.value = 'ready';
  } catch {
    loadState.value = 'error';
  }
});

watch(
  () => props.language,
  (language) => {
    editorController?.setLanguage(language);
  },
);

watch(
  () => props.readOnly,
  (readOnly) => {
    editorController?.setReadOnly(Boolean(readOnly));
  },
);

watch(
  () => props.value,
  (value) => {
    if (!editorController || editorController.getValue() === value) {
      return;
    }

    suppressChangeEmit = true;
    editorController.setValue(value);
    suppressChangeEmit = false;
  },
);

onBeforeUnmount(() => {
  editorController?.dispose();
  editorController = null;
});
</script>

<template>
  <div class="surface-host" :class="{ 'surface-host--mockup': variant === 'mockup' }">
    <p v-if="loadState === 'loading'" class="surface-host__status">Loading Monaco editor…</p>
    <p v-else-if="loadState === 'error'" class="surface-host__status">Editor host unavailable</p>
    <div v-if="variant !== 'mockup'" class="surface-host__meta">
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
    <div class="surface-host__body" @click="focusEditor">
      <div ref="containerRef" class="surface-host__frame" aria-label="Monaco editor host" />
    </div>
  </div>
</template>
