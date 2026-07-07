<script setup lang="ts">
import { computed, ref } from 'vue';

import {
  deriveAgentReportTitle,
  renderAgentMessageMarkdown,
  shouldOfferOpenInEditor,
  splitAgentMessageForPreview,
} from '../../lib/agent-message-markdown';
import {
  persistAgentMessagePreviewEnabled,
  readAgentMessagePreviewEnabled,
} from '../../lib/agent-message-preview-prefs';
import { useShellStore } from '../../stores/shell';

const props = withDefaults(
  defineProps<{
    blockId: string;
    content: string;
    allowOpenInEditor?: boolean;
  }>(),
  {
    allowOpenInEditor: true,
  },
);

const shell = useShellStore();
const copied = ref(false);
let copiedTimeout: ReturnType<typeof setTimeout> | null = null;

const parts = computed(() => splitAgentMessageForPreview(props.content));
const previewEnabled = ref(readAgentMessagePreviewEnabled(props.blockId) ?? true);
const canOpenInEditor = computed(
  () => props.allowOpenInEditor && shouldOfferOpenInEditor(props.content, true),
);
const previewHtml = computed(() => renderAgentMessageMarkdown(props.content));

function setPreviewMode(enabled: boolean): void {
  previewEnabled.value = enabled;
  persistAgentMessagePreviewEnabled(props.blockId, enabled);
}

async function copyMarkdownSource(): Promise<void> {
  if (typeof navigator === 'undefined' || !navigator.clipboard) {
    return;
  }
  try {
    await navigator.clipboard.writeText(parts.value.markdownSource);
    copied.value = true;
    if (copiedTimeout) {
      clearTimeout(copiedTimeout);
    }
    copiedTimeout = setTimeout(() => {
      copied.value = false;
      copiedTimeout = null;
    }, 1500);
  } catch {
    copied.value = false;
  }
}

function openInEditor(): void {
  if (!canOpenInEditor.value) {
    return;
  }
  shell.openAgentContentInEditor({
    title: deriveAgentReportTitle(parts.value.markdownSource),
    content: parts.value.markdownSource,
    preferPreview: true,
  });
}
</script>

<template>
  <div class="conversation-seam__markdown-block">
    <div class="conversation-seam__markdown-toolbar">
      <div
        class="conversation-seam__markdown-mode-toggle"
        role="group"
        aria-label="Markdown view mode"
      >
        <button
          type="button"
          class="conversation-seam__markdown-mode-button"
          :class="{ 'conversation-seam__markdown-mode-button--active': previewEnabled }"
          :aria-pressed="previewEnabled"
          @click="setPreviewMode(true)"
        >
          Preview
        </button>
        <button
          type="button"
          class="conversation-seam__markdown-mode-button"
          :class="{ 'conversation-seam__markdown-mode-button--active': !previewEnabled }"
          :aria-pressed="!previewEnabled"
          @click="setPreviewMode(false)"
        >
          Raw
        </button>
      </div>
      <button
        v-if="canOpenInEditor"
        type="button"
        class="conversation-seam__block-button"
        title="Open this report in the center editor"
        @click="openInEditor"
      >
        Open in editor
      </button>
      <button
        type="button"
        class="conversation-seam__block-button"
        @click="copyMarkdownSource"
      >
        {{ copied ? 'Copied' : 'Copy' }}
      </button>
    </div>

    <p v-if="parts.preamble" class="conversation-seam__preamble">
      {{ parts.preamble }}
    </p>

    <div
      v-if="previewEnabled"
      class="conversation-seam__content conversation-seam__content--markdown"
      v-html="previewHtml"
    />
    <pre
      v-else
      class="conversation-seam__content conversation-seam__content--raw"
    >{{ parts.markdownSource }}</pre>

    <p v-if="parts.postamble" class="conversation-seam__postamble">
      {{ parts.postamble }}
    </p>
  </div>
</template>
