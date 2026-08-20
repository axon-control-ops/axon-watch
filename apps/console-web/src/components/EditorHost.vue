<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';

import { createMonacoEditor } from '../lib/create-monaco-editor';
import {
  EDITOR_SURFACE_LAYOUT_EVENT,
} from '../lib/editor-surface-layout';
import type { EditorDocumentLanguage } from '../lib/workspace-documents';
import type { EditorSelectionSnapshot } from '../lib/create-monaco-editor';

export type EditorRevealRequest = {
  line?: number;
  searchText?: string;
  nonce: number;
};

const props = defineProps<{
  documentKey: string;
  title: string;
  value: string;
  language: EditorDocumentLanguage;
  description: string;
  readOnly?: boolean;
  dirty?: boolean;
  variant?: 'default' | 'mockup';
  themeProfile?: 'mockup' | 'cursor';
  minimapEnabled?: boolean;
  revealRequest?: EditorRevealRequest | null;
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
let mountedDocumentKey = '';
let resizeObserver: ResizeObserver | null = null;
let editorSurfaceLayoutListener: (() => void) | null = null;

function scheduleEditorLayout(): void {
  if (!editorController) {
    return;
  }
  editorController.layout();
  requestAnimationFrame(() => {
    editorController?.layout();
    requestAnimationFrame(() => {
      editorController?.layout();
    });
  });
}

function applyDocumentToEditor(): void {
  if (!editorController) {
    return;
  }

  if (mountedDocumentKey === props.documentKey) {
    if (editorController.getValue() !== props.value) {
      suppressChangeEmit = true;
      editorController.setValue(props.value);
      suppressChangeEmit = false;
    }
    editorController.setReadOnly(Boolean(props.readOnly));
    scheduleEditorLayout();
    return;
  }

  editorController.replaceDocument(props.value, props.language);
  editorController.setReadOnly(Boolean(props.readOnly));
  mountedDocumentKey = props.documentKey;
  scheduleEditorLayout();
}

function focusEditor(): void {
  editorController?.focus();
}

function applyRevealRequest(request: EditorRevealRequest | null | undefined): void {
  if (!editorController || !request) {
    return;
  }
  if (request.line && request.line > 0) {
    editorController.revealLine(request.line);
    return;
  }
  if (request.searchText) {
    editorController.findAndReveal(request.searchText);
  }
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
      themeProfile: props.themeProfile,
      minimapEnabled: props.minimapEnabled,
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
    mountedDocumentKey = props.documentKey;
    loadState.value = 'ready';
    applyDocumentToEditor();
    applyRevealRequest(props.revealRequest);
    if (typeof ResizeObserver !== 'undefined' && containerRef.value) {
      resizeObserver = new ResizeObserver(() => {
        scheduleEditorLayout();
      });
      resizeObserver.observe(containerRef.value);
    }
    scheduleEditorLayout();
    editorSurfaceLayoutListener = () => {
      scheduleEditorLayout();
    };
    window.addEventListener(EDITOR_SURFACE_LAYOUT_EVENT, editorSurfaceLayoutListener);
  } catch {
    loadState.value = 'error';
  }
});

watch(
  () => props.revealRequest?.nonce,
  () => {
    applyRevealRequest(props.revealRequest);
  },
);

watch(
  () => props.minimapEnabled,
  (minimapEnabled) => {
    if (minimapEnabled !== undefined) {
      editorController?.setMinimapEnabled(minimapEnabled);
    }
  },
);

watch(
  () => [props.documentKey, props.value, props.language, props.readOnly] as const,
  () => {
    applyDocumentToEditor();
  },
);

onBeforeUnmount(() => {
  if (editorSurfaceLayoutListener) {
    window.removeEventListener(EDITOR_SURFACE_LAYOUT_EVENT, editorSurfaceLayoutListener);
    editorSurfaceLayoutListener = null;
  }
  resizeObserver?.disconnect();
  resizeObserver = null;
  editorController?.dispose();
  editorController = null;
  mountedDocumentKey = '';
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
    <div class="surface-host__body surface-host__body--editor" @click="focusEditor">
      <div ref="containerRef" class="surface-host__frame surface-host__frame--editor" aria-label="Monaco editor host" />
    </div>
  </div>
</template>
