<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import {
  renderAgentMessageMarkdown,
  splitAgentMessageForPreview,
} from '../../lib/agent-message-markdown';
import {
  persistAgentMessagePreviewEnabled,
  resolveAgentMessagePreviewEnabled,
} from '../../lib/agent-message-preview-prefs';

const props = defineProps<{
  blockId: string;
  content: string;
}>();

const copied = ref(false);
let copiedTimeout: ReturnType<typeof setTimeout> | null = null;

const parts = computed(() => splitAgentMessageForPreview(props.content));
const previewEnabled = ref(
  resolveAgentMessagePreviewEnabled(props.blockId, parts.value.hasMarkdownPreview),
);

watch(
  () => props.blockId,
  (blockId) => {
    previewEnabled.value = resolveAgentMessagePreviewEnabled(
      blockId,
      parts.value.hasMarkdownPreview,
    );
  },
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
