<script setup lang="ts">
import { computed, ref } from 'vue';

import { renderAgentMessageMarkdown } from '../../lib/agent-message-markdown';
import {
  extractProposedFileContentFromDiff,
  isMarkdownAgentEditPath,
  truncateDiffLinesForDock,
  truncateMarkdownForDockPreview,
} from '../../lib/ide-agent-edit-review';
import { diffLineTone, normalizeEditedFilePath } from '../../lib/agent-transcript-blocks';
import { handleMarkdownContainerClick } from '../../lib/markdown-link-click';
import { resolveThreadImageUrl } from '../../lib/thread-image-url';
import { isImageFilePath, isPdfFilePath } from '../../lib/workspace-file-language';
import { useShellStore } from '../../stores/shell';
import ImagePreviewLightbox from './ImagePreviewLightbox.vue';

const props = defineProps<{
  path: string;
  added: number;
  removed: number;
  diff: string;
  open: boolean;
}>();

const shell = useShellStore();
// Collapsed by default: expanded markdown/diff previews are expensive, and a
// long agent turn can otherwise freeze the main thread while streaming.
const expanded = ref(false);
const lightboxOpen = ref(false);

const normalizedPath = computed(() => normalizeEditedFilePath(props.path));
const isMarkdown = computed(() => isMarkdownAgentEditPath(normalizedPath.value));
const isImage = computed(() => isImageFilePath(normalizedPath.value));
const isPdf = computed(() => isPdfFilePath(normalizedPath.value));
const isCanvasFile = computed(() => isImage.value || isPdf.value);

const openActionLabel = computed(() => {
  if (props.open) {
    return 'Review streaming edit';
  }
  if (isImage.value) {
    return 'Open in canvas';
  }
  if (isPdf.value) {
    return 'Open PDF preview';
  }
  return 'Open in editor';
});

const imageUrl = computed(() => {
  if (!isImage.value) {
    return '';
  }
  return resolveThreadImageUrl(normalizedPath.value, {
    workspaceId: shell.currentWorkspace?.workspace_id ?? null,
  });
});

const markdownPreview = computed(() => {
  if (!expanded.value || !isMarkdown.value || !props.diff.trim()) {
    return { preview: '', truncated: false, html: '' };
  }
  const proposed = extractProposedFileContentFromDiff(props.diff);
  const truncated = truncateMarkdownForDockPreview(proposed);
  return {
    ...truncated,
    html: truncated.preview ? renderAgentMessageMarkdown(truncated.preview) : '',
  };
});

const diffPreview = computed(() => {
  if (!expanded.value || isMarkdown.value || isCanvasFile.value) {
    return { lines: [] as Array<{ text: string; tone: string }>, truncated: false };
  }
  const truncated = truncateDiffLinesForDock(props.diff);
  return {
    lines: truncated.lines.map((text) => ({ text, tone: diffLineTone(text) })),
    truncated: truncated.truncated,
  };
});

function toggle(): void {
  expanded.value = !expanded.value;
}

function openInEditor(): void {
  shell.openAgentEditReview({
    path: normalizedPath.value,
    added: props.added,
    removed: props.removed,
    diff: props.diff,
    open: props.open,
  });
}

function openLightbox(): void {
  if (!imageUrl.value) {
    return;
  }
  lightboxOpen.value = true;
}

function closeLightbox(): void {
  lightboxOpen.value = false;
}

function handlePreviewClick(event: MouseEvent): void {
  handleMarkdownContainerClick(event, {
    openWorkspaceFile: (path) => shell.openWorkspaceFile(path),
    baseFilePath: normalizedPath.value,
  });
}
</script>

<template>
  <div class="agent-block agent-block--edit">
    <div class="agent-block__edit-header">
      <button
        type="button"
        class="agent-block__edit-toggle"
        :aria-expanded="expanded"
        :title="expanded ? 'Collapse edit' : 'Expand edit'"
        @click="toggle"
      >
        <span class="agent-block__edit-icon" aria-hidden="true">
          {{ expanded ? '▾' : '▸' }}
        </span>
      </button>
      <button
        type="button"
        class="agent-block__edit-path agent-block__edit-path--link"
        :title="`${openActionLabel}: ${normalizedPath}`"
        @click="openInEditor"
      >
        {{ normalizedPath }}
      </button>
      <span class="agent-block__edit-stat agent-block__edit-stat--add">+{{ added }}</span>
      <span class="agent-block__edit-stat agent-block__edit-stat--remove">-{{ removed }}</span>
      <button
        v-if="!open"
        type="button"
        class="agent-block__edit-open-action"
        :title="openActionLabel"
        @click="openInEditor"
      >
        {{ isCanvasFile ? 'Canvas' : 'Open' }}
      </button>
      <span v-if="open" class="agent-block__edit-streaming">streaming</span>
    </div>

    <div v-if="expanded" class="agent-block__edit-body">
      <div v-if="isImage && imageUrl" class="agent-block__edit-canvas">
        <button
          type="button"
          class="agent-block__edit-canvas-thumb"
          :title="`Preview ${normalizedPath}`"
          @click="openLightbox"
        >
          <img
            class="agent-block__edit-canvas-img"
            :src="imageUrl"
            :alt="normalizedPath"
            loading="lazy"
          >
        </button>
        <button type="button" class="agent-block__edit-open-full" @click="openInEditor">
          Open in canvas
        </button>
      </div>
      <div v-else-if="isPdf" class="agent-block__edit-canvas agent-block__edit-canvas--pdf">
        <p class="agent-block__edit-empty">PDF ready — open to preview in the editor canvas.</p>
        <button type="button" class="agent-block__edit-open-full" @click="openInEditor">
          Open PDF preview
        </button>
      </div>
      <div
        v-else-if="isMarkdown && markdownPreview.html"
        class="agent-block__edit-markdown conversation-seam__content conversation-seam__content--markdown"
        v-html="markdownPreview.html"
        @click="handlePreviewClick"
      />
      <pre
        v-else-if="diffPreview.lines.length"
        class="agent-block__edit-diff"
      ><span
        v-for="(diffLine, diffIndex) in diffPreview.lines"
        :key="diffIndex"
        class="agent-block__diff-line"
        :class="`agent-block__diff-line--${diffLine.tone}`"
      >{{ diffLine.text }}
</span></pre>
      <p v-else class="agent-block__edit-empty">No diff captured yet.</p>

      <button
        v-if="markdownPreview.truncated || diffPreview.truncated"
        type="button"
        class="agent-block__edit-open-full"
        @click="openInEditor"
      >
        Open full file in editor
      </button>
    </div>

    <ImagePreviewLightbox
      :preview="lightboxOpen && imageUrl ? { url: imageUrl, filename: normalizedPath.split('/').pop() || normalizedPath } : null"
      @close="closeLightbox"
    />
  </div>
</template>
