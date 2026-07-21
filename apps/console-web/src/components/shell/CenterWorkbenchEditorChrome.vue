<script setup lang="ts">
import { computed, ref } from 'vue';

import WorkbenchIcon from '../WorkbenchIcon.vue';
import {
  editorTabLabelForDocument,
  editorTabLabelsForDocuments,
} from '../../lib/editor-tab-labels';
import type { EditorBreadcrumbSegment } from '../../lib/editor-breadcrumb-view';
import type { WorkspaceDocumentDescriptor } from '../../lib/workspace-documents';

const props = defineProps<{
  activeEditorDocumentId: string | null;
  editorTabDocuments: WorkspaceDocumentDescriptor[];
  editorBreadcrumbSegments: EditorBreadcrumbSegment[];
  activeWorkspaceFilePath: string | null;
}>();

const emit = defineEmits<{
  selectDocument: [documentId: string];
  closeDocument: [documentId: string];
  createFile: [];
  renameFile: [];
  breadcrumbClick: [segment: EditorBreadcrumbSegment];
}>();

const editorTabsRef = ref<HTMLElement | null>(null);
const editorTabLabels = computed(() => editorTabLabelsForDocuments(props.editorTabDocuments));

function editorTabLabel(documentId: string, document: { title: string }): string {
  return editorTabLabelForDocument(
    props.editorTabDocuments.find((entry) => entry.id === documentId) ?? {
      id: documentId,
      title: document.title,
      language: 'markdown',
      value: '',
      description: '',
      source: 'draft',
    },
    editorTabLabels.value,
  );
}

function handleEditorTabClose(event: MouseEvent, documentId: string): void {
  event.stopPropagation();
  emit('closeDocument', documentId);
}

function handleEditorTabsWheel(event: WheelEvent): void {
  const tabs = editorTabsRef.value;
  if (!tabs) {
    return;
  }
  const delta =
    Math.abs(event.deltaX) > Math.abs(event.deltaY) ? event.deltaX : event.deltaY;
  if (delta === 0 || tabs.scrollWidth <= tabs.clientWidth) {
    return;
  }
  event.preventDefault();
  tabs.scrollLeft += delta;
}
</script>

<template>
  <header class="editor-chrome editor-chrome--mockup">
    <div class="editor-tabbar editor-tabbar--mockup">
      <div
        ref="editorTabsRef"
        class="editor-tabbar__tabs"
        role="tablist"
        aria-label="Open editor tabs"
        @wheel="handleEditorTabsWheel"
      >
        <div
          v-for="document in editorTabDocuments"
          :key="document.id"
          role="tab"
          class="editor-tabbar__tab"
          :class="{
            'editor-tabbar__tab--active': activeEditorDocumentId === document.id,
            'editor-tabbar__tab--dirty': document.dirty,
          }"
          :aria-selected="activeEditorDocumentId === document.id"
        >
          <button
            type="button"
            class="editor-tabbar__tab-select"
            @click="emit('selectDocument', document.id)"
          >
            <WorkbenchIcon name="file" class="editor-tabbar__file-icon" />
            <span class="editor-tabbar__label">{{ editorTabLabel(document.id, document) }}</span>
          </button>
          <button
            type="button"
            class="editor-tabbar__close"
            title="Close editor tab"
            aria-label="Close editor tab"
            @click="handleEditorTabClose($event, document.id)"
          >
            <WorkbenchIcon name="close" class="editor-tabbar__close-icon" />
          </button>
        </div>
      </div>
      <div class="editor-tabbar__tools" aria-label="Editor actions">
        <button
          type="button"
          class="editor-tabbar__tool-button"
          title="New file"
          aria-label="New file"
          @click="emit('createFile')"
        >
          <WorkbenchIcon name="new-file" class="editor-tabbar__tool" />
        </button>
        <button type="button" class="editor-tabbar__tool-button" title="Split editor" aria-label="Split editor">
          <WorkbenchIcon name="split" class="editor-tabbar__tool" />
        </button>
        <button
          type="button"
          class="editor-tabbar__tool-button"
          title="Rename active file"
          aria-label="Rename active file"
          :disabled="!activeWorkspaceFilePath"
          @click="emit('renameFile')"
        >
          <WorkbenchIcon name="more" class="editor-tabbar__tool" />
        </button>
      </div>
    </div>

    <nav class="editor-breadcrumb editor-breadcrumb--mockup" aria-label="Editor location">
      <template v-for="(segment, index) in editorBreadcrumbSegments" :key="segment.id">
        <span v-if="index > 0" class="editor-breadcrumb__sep" aria-hidden="true">›</span>
        <button
          type="button"
          class="editor-breadcrumb__segment"
          :class="{
            'editor-breadcrumb__segment--symbol': segment.kind === 'symbol',
            'editor-breadcrumb__segment--active': index === editorBreadcrumbSegments.length - 1,
          }"
          :disabled="!segment.revealLine"
          @click="emit('breadcrumbClick', segment)"
        >
          <span>{{ segment.label }}</span>
        </button>
      </template>
    </nav>
  </header>
</template>
