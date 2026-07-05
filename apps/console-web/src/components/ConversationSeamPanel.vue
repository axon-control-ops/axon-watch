<script setup lang="ts">
import { nextTick, ref, watch } from 'vue';

import {
  renderAgentMessageMarkdown,
  shouldOfferMarkdownPreview,
  splitAgentMessageForPreview,
} from '../lib/agent-message-markdown';
import {
  persistAgentMarkdownPreviewDefault,
  persistAgentMessagePreviewEnabled,
  resolveAgentMessagePreviewEnabled,
} from '../lib/agent-message-preview-prefs';
import { useShellStore } from '../stores/shell';

const shell = useShellStore();
const listRef = ref<HTMLElement | null>(null);
const previewByMessageId = ref<Record<string, boolean>>({});

function syncPreviewStateFromStorage(): void {
  const next: Record<string, boolean> = {};
  for (const message of shell.threadMessages) {
    if (message.role !== 'agent' || !shouldOfferMarkdownPreview(message.content)) {
      continue;
    }
    next[message.message_id] = resolveAgentMessagePreviewEnabled(
      message.message_id,
      true,
    );
  }
  previewByMessageId.value = next;
}

async function scrollToLatestMessage(): Promise<void> {
  await nextTick();
  const list = listRef.value;
  if (!list) {
    return;
  }

  list.scrollTop = list.scrollHeight;
}

function isPreviewMode(messageId: string, content: string): boolean {
  if (previewByMessageId.value[messageId] !== undefined) {
    return previewByMessageId.value[messageId];
  }

  return resolveAgentMessagePreviewEnabled(messageId, shouldOfferMarkdownPreview(content));
}

function togglePreview(messageId: string, content: string): void {
  const next = !isPreviewMode(messageId, content);
  previewByMessageId.value = {
    ...previewByMessageId.value,
    [messageId]: next,
  };
  persistAgentMessagePreviewEnabled(messageId, next);
  persistAgentMarkdownPreviewDefault(next);
}

function previewHtml(content: string): string {
  return renderAgentMessageMarkdown(content);
}

function previewParts(content: string) {
  return splitAgentMessageForPreview(content);
}

watch(
  () => shell.threadMessages,
  () => {
    syncPreviewStateFromStorage();
    void scrollToLatestMessage();
  },
  { immediate: true, deep: true },
);
</script>

<template>
  <div class="conversation-seam">
    <ul
      v-if="shell.threadMessages.length"
      ref="listRef"
      class="conversation-seam__list"
    >
      <li
        v-for="message in shell.threadMessages"
        :key="message.message_id"
        class="conversation-seam__item"
        :class="`conversation-seam__item--${message.role}`"
      >
        <div class="conversation-seam__meta">
          <span class="conversation-seam__role">{{ message.role }}</span>
          <time class="conversation-seam__time" :datetime="message.created_at">
            {{ message.created_at }}
          </time>
          <button
            v-if="message.role === 'agent' && shouldOfferMarkdownPreview(message.content)"
            type="button"
            class="conversation-seam__preview-toggle"
            :aria-pressed="isPreviewMode(message.message_id, message.content)"
            @click="togglePreview(message.message_id, message.content)"
          >
            {{ isPreviewMode(message.message_id, message.content) ? 'Raw' : 'Preview' }}
          </button>
        </div>
        <p
          v-if="message.role !== 'agent'"
          class="conversation-seam__content"
        >
          {{ message.content }}
        </p>
        <template v-else-if="isPreviewMode(message.message_id, message.content)">
          <p
            v-if="previewParts(message.content).preamble"
            class="conversation-seam__preamble"
          >
            {{ previewParts(message.content).preamble }}
          </p>
          <div
            class="conversation-seam__content conversation-seam__content--agent conversation-seam__content--markdown"
            v-html="previewHtml(message.content)"
          />
        </template>
        <pre
          v-else
          class="conversation-seam__content conversation-seam__content--agent"
        >{{ message.content }}</pre>
      </li>
    </ul>
    <p v-else class="region-copy conversation-seam__empty">No active conversation</p>
  </div>
</template>
