<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import AgentResearchBlock from './ide/AgentResearchBlock.vue';
import AgentMarkdownBlock from './ide/AgentMarkdownBlock.vue';
import { useConversationSeamScroll } from '../composables/useConversationSeamScroll';
import {
  shouldOfferMarkdownPreview,
} from '../lib/agent-message-markdown';
import {
  agentContentLooksLikeErrorDump,
  formatThreadRole,
  formatThreadTimestamp,
  shouldCollapseSystemMessage,
  shortenRunId,
  summarizeAgentErrorContent,
  systemMessagePreview,
} from '../lib/thread-message-view';
import {
  agentContentHasTranscriptBlocks,
  diffLineTone,
  parseAgentTranscriptBlocks,
  thinkingPreview,
} from '../lib/agent-transcript-blocks';
import { useShellStore } from '../stores/shell';

const shell = useShellStore();
const conversationMessages = computed(() =>
  shell.layoutMode === 'ide' ? shell.threadMessages : shell.operatorThreadMessages,
);
const showAgentWorking = computed(
  () =>
    shell.agentStreamActive ||
    (shell.layoutMode === 'ide' && Boolean(shell.ideComposerActivity)),
);
const agentWorkingLabel = computed(() => {
  if (shell.agentStreamActive && shell.agentStreamMessageId) {
    return shell.ideComposerActivity?.label?.includes('Full Access')
      ? 'Full Access — streaming runtime output…'
      : 'Streaming agent reply…';
  }
  if (shell.agentStreamActive) {
    return 'Agent is thinking…';
  }
  return shell.ideComposerActivity?.label ?? 'Agent is working…';
});
const rootRef = ref<HTMLElement | null>(null);
const listRef = ref<HTMLElement | null>(null);
const expandedErrorByMessageId = ref<Record<string, boolean>>({});
const expandedSystemByMessageId = ref<Record<string, boolean>>({});

const { handleWheel, handleContentChange } = useConversationSeamScroll({
  rootRef,
  listRef,
  onContentChange: () => undefined,
});

function toggleErrorExpanded(messageId: string): void {
  expandedErrorByMessageId.value = {
    ...expandedErrorByMessageId.value,
    [messageId]: !expandedErrorByMessageId.value[messageId],
  };
}

function isMarkdownBlock(content: string): boolean {
  return shouldOfferMarkdownPreview(content) && !isErrorDump(content);
}

function isErrorDump(content: string): boolean {
  return agentContentLooksLikeErrorDump(content);
}

function isErrorExpanded(messageId: string): boolean {
  return Boolean(expandedErrorByMessageId.value[messageId]);
}

function toggleSystemExpanded(messageId: string): void {
  expandedSystemByMessageId.value = {
    ...expandedSystemByMessageId.value,
    [messageId]: !expandedSystemByMessageId.value[messageId],
  };
}

function isSystemExpanded(messageId: string): boolean {
  return Boolean(expandedSystemByMessageId.value[messageId]);
}

function isStreamingMessage(messageId: string): boolean {
  return shell.agentStreamActive && shell.agentStreamMessageId === messageId;
}

const expandedThinkingKeys = ref<Record<string, boolean>>({});
const collapsedEditKeys = ref<Record<string, boolean>>({});

function hasTranscriptBlocks(content: string): boolean {
  return agentContentHasTranscriptBlocks(content);
}

function transcriptSegments(content: string) {
  return parseAgentTranscriptBlocks(content);
}

function segmentKey(messageId: string, index: number): string {
  return `${messageId}:${index}`;
}

function isThinkingExpanded(key: string, open: boolean): boolean {
  return expandedThinkingKeys.value[key] ?? open;
}

function toggleThinking(key: string, open: boolean): void {
  expandedThinkingKeys.value = {
    ...expandedThinkingKeys.value,
    [key]: !isThinkingExpanded(key, open),
  };
}

function isEditExpanded(key: string): boolean {
  return !(collapsedEditKeys.value[key] ?? false);
}

function toggleEdit(key: string): void {
  collapsedEditKeys.value = {
    ...collapsedEditKeys.value,
    [key]: isEditExpanded(key),
  };
}

function diffLines(diff: string): Array<{ text: string; tone: string }> {
  return diff
    .split('\n')
    .map((line) => ({ text: line, tone: diffLineTone(line) }));
}

function restoreMessageToComposer(content: string): void {
  shell.restoreComposerDraft(content);
}

function isEmptyStreamingAgent(message: { role: string; message_id: string; content: string }): boolean {
  return message.role === 'agent' && !message.content.trim() && isStreamingMessage(message.message_id);
}

watch(
  conversationMessages,
  () => {
    handleContentChange();
  },
  { immediate: true, deep: true },
);
</script>

<template>
  <div ref="rootRef" class="conversation-seam" @wheel.capture="handleWheel">
    <ul
      v-if="conversationMessages.length"
      ref="listRef"
      class="conversation-seam__list"
    >
      <li
        v-for="message in conversationMessages"
        :key="message.message_id"
        class="conversation-seam__item"
        :class="`conversation-seam__item--${message.role}`"
      >
        <div class="conversation-seam__meta">
          <span class="conversation-seam__role">{{ formatThreadRole(message.role) }}</span>
          <span
            v-if="message.run_id"
            class="conversation-seam__run-chip"
            :title="message.run_id"
          >
            run {{ shortenRunId(message.run_id) }}
          </span>
          <time class="conversation-seam__time" :datetime="message.created_at">
            {{ formatThreadTimestamp(message.created_at) }}
          </time>
          <div v-if="message.role === 'operator'" class="conversation-seam__meta-actions">
            <button
              type="button"
              class="conversation-seam__meta-button"
              title="Load this request back into the composer"
              @click="restoreMessageToComposer(message.content)"
            >
              Resend
            </button>
          </div>
        </div>

        <p
          v-if="message.role === 'system' && shouldCollapseSystemMessage(message.content) && !isSystemExpanded(message.message_id)"
          class="conversation-seam__content conversation-seam__content--system-collapsed"
        >
          {{ systemMessagePreview(message.content) }}
          <button
            type="button"
            class="conversation-seam__expand-toggle conversation-seam__expand-toggle--inline"
            @click="toggleSystemExpanded(message.message_id)"
          >
            Show
          </button>
        </p>

        <template v-else-if="message.role === 'system' && shouldCollapseSystemMessage(message.content)">
          <p class="conversation-seam__content">
            {{ message.content }}
          </p>
          <button
            type="button"
            class="conversation-seam__expand-toggle"
            @click="toggleSystemExpanded(message.message_id)"
          >
            Collapse
          </button>
        </template>

        <p
          v-else-if="message.role !== 'agent'"
          class="conversation-seam__content"
        >
          {{ message.content }}
        </p>

        <p
          v-else-if="isEmptyStreamingAgent(message)"
          class="conversation-seam__content conversation-seam__content--agent conversation-seam__content--typing"
        >
          <span class="conversation-seam__typing-dot" aria-hidden="true" />
          Agent is thinking…
        </p>

        <div
          v-else-if="hasTranscriptBlocks(message.content)"
          class="conversation-seam__blocks"
        >
          <template
            v-for="(segment, segmentIndex) in transcriptSegments(message.content)"
            :key="segmentKey(message.message_id, segmentIndex)"
          >
            <div
              v-if="segment.kind === 'thinking'"
              class="agent-block agent-block--thinking"
              :class="{ 'agent-block--thinking-live': segment.open && isStreamingMessage(message.message_id) }"
            >
              <button
                type="button"
                class="agent-block__thinking-toggle"
                @click="toggleThinking(segmentKey(message.message_id, segmentIndex), segment.open)"
              >
                <span class="agent-block__thinking-icon" aria-hidden="true">
                  {{ isThinkingExpanded(segmentKey(message.message_id, segmentIndex), segment.open) ? '▾' : '▸' }}
                </span>
                <span v-if="segment.open && isStreamingMessage(message.message_id)">
                  {{ segment.text.trim() ? thinkingPreview(segment.text, 120) : 'Thinking…' }}
                </span>
                <span v-else class="agent-block__thinking-preview">
                  Thought — {{ thinkingPreview(segment.text) }}
                </span>
              </button>
              <p
                v-if="isThinkingExpanded(segmentKey(message.message_id, segmentIndex), segment.open)"
                class="agent-block__thinking-body"
              >
                {{ segment.text }}
              </p>
            </div>

            <div v-else-if="segment.kind === 'tool'" class="agent-block agent-block--tool">
              <span class="agent-block__tool-dot" aria-hidden="true" />
              <span>{{ segment.label }}</span>
            </div>

            <AgentResearchBlock
              v-else-if="segment.kind === 'research'"
              :query="segment.query"
              :items="segment.items"
              :live="segment.open && isStreamingMessage(message.message_id)"
            />

            <div v-else-if="segment.kind === 'terminal'" class="agent-block agent-block--terminal">
              <div class="agent-block__terminal-header">
                <span class="agent-block__terminal-prompt" aria-hidden="true">$</span>
                <code class="agent-block__terminal-command">{{ segment.command }}</code>
                <span
                  v-if="segment.open && isStreamingMessage(message.message_id)"
                  class="agent-block__terminal-running"
                >running…</span>
              </div>
              <pre
                v-if="segment.output"
                class="agent-block__terminal-output"
              >{{ segment.output }}</pre>
            </div>

            <div v-else-if="segment.kind === 'edit'" class="agent-block agent-block--edit">
              <button
                type="button"
                class="agent-block__edit-header"
                @click="toggleEdit(segmentKey(message.message_id, segmentIndex))"
              >
                <span class="agent-block__edit-icon" aria-hidden="true">
                  {{ isEditExpanded(segmentKey(message.message_id, segmentIndex)) ? '▾' : '▸' }}
                </span>
                <span class="agent-block__edit-path">{{ segment.path }}</span>
                <span class="agent-block__edit-stat agent-block__edit-stat--add">+{{ segment.added }}</span>
                <span class="agent-block__edit-stat agent-block__edit-stat--remove">-{{ segment.removed }}</span>
              </button>
              <pre
                v-if="isEditExpanded(segmentKey(message.message_id, segmentIndex)) && segment.diff"
                class="agent-block__edit-diff"
              ><span
                v-for="(diffLine, diffIndex) in diffLines(segment.diff)"
                :key="diffIndex"
                class="agent-block__diff-line"
                :class="`agent-block__diff-line--${diffLine.tone}`"
              >{{ diffLine.text }}
</span></pre>
            </div>

            <AgentMarkdownBlock
              v-else-if="isMarkdownBlock(segment.text)"
              :block-id="segmentKey(message.message_id, segmentIndex)"
              :content="segment.text"
            />

            <p
              v-else
              class="agent-block agent-block--text conversation-seam__content conversation-seam__content--agent"
            >
              {{ segment.text }}
            </p>
          </template>
          <span
            v-if="isStreamingMessage(message.message_id)"
            class="conversation-seam__stream-cursor"
            aria-hidden="true"
          >▍</span>
        </div>

        <template v-else-if="isErrorDump(message.content) && !isStreamingMessage(message.message_id)">
          <p class="conversation-seam__content conversation-seam__content--agent conversation-seam__content--error">
            {{ summarizeAgentErrorContent(message.content) }}
          </p>
          <button
            type="button"
            class="conversation-seam__expand-toggle"
            @click="toggleErrorExpanded(message.message_id)"
          >
            {{ isErrorExpanded(message.message_id) ? 'Hide details' : 'Show details' }}
          </button>
          <pre
            v-if="isErrorExpanded(message.message_id)"
            class="conversation-seam__content conversation-seam__content--agent conversation-seam__content--error-detail"
          >{{ message.content }}</pre>
        </template>

        <AgentMarkdownBlock
          v-else-if="isMarkdownBlock(message.content)"
          :block-id="message.message_id"
          :content="message.content"
        />

        <pre
          v-else
          class="conversation-seam__content conversation-seam__content--agent"
          :class="{
            'conversation-seam__content--streaming': isStreamingMessage(message.message_id),
            'conversation-seam__content--streaming-full-access':
              isStreamingMessage(message.message_id) &&
              shell.ideComposerActivity?.executionAccess === 'full',
          }"
        >{{ message.content }}<span
          v-if="isStreamingMessage(message.message_id)"
          class="conversation-seam__stream-cursor"
          aria-hidden="true"
        >▍</span></pre>
      </li>
      <li
        v-if="showAgentWorking && !shell.agentStreamMessageId"
        class="conversation-seam__item conversation-seam__item--agent conversation-seam__item--typing"
        :class="{
          'conversation-seam__item--full-access':
            shell.ideComposerActivity?.executionAccess === 'full',
        }"
      >
        <div class="conversation-seam__meta">
          <span class="conversation-seam__role">AGENT</span>
          <span
            v-if="shell.ideComposerActivity?.executionAccess === 'full'"
            class="conversation-seam__access-chip conversation-seam__access-chip--full"
          >
            Full Access
          </span>
        </div>
        <p
          class="conversation-seam__content conversation-seam__content--agent conversation-seam__content--typing"
          :class="{
            'conversation-seam__content--typing-full-access':
              shell.ideComposerActivity?.executionAccess === 'full',
          }"
        >
          <span class="conversation-seam__typing-dot" aria-hidden="true" />
          {{ agentWorkingLabel }}
        </p>
      </li>
    </ul>
    <p v-else class="region-copy conversation-seam__empty">No active conversation</p>
  </div>
</template>
