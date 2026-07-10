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
import { useShellStore } from '../../stores/shell';

const props = defineProps<{
  path: string;
  added: number;
  removed: number;
  diff: string;
  open: boolean;
}>();

const shell = useShellStore();
const expanded = ref(true);

const normalizedPath = computed(() => normalizeEditedFilePath(props.path));
const isMarkdown = computed(() => isMarkdownAgentEditPath(normalizedPath.value));

const markdownPreview = computed(() => {
  if (!isMarkdown.value || !props.diff.trim()) {
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
  if (isMarkdown.value) {
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
        :title="`Open ${normalizedPath} in editor`"
        @click="openInEditor"
      >
        {{ normalizedPath }}
      </button>
      <span class="agent-block__edit-stat agent-block__edit-stat--add">+{{ added }}</span>
      <span class="agent-block__edit-stat agent-block__edit-stat--remove">-{{ removed }}</span>
      <span v-if="open" class="agent-block__edit-streaming">streaming</span>
    </div>

    <div v-if="expanded" class="agent-block__edit-body">
      <div
        v-if="isMarkdown && markdownPreview.html"
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
  </div>
</template>
