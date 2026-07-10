<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import AgentResearchBlock from './ide/AgentResearchBlock.vue';
import AgentMarkdownBlock from './ide/AgentMarkdownBlock.vue';
import AgentFileReadBlock from './ide/AgentFileReadBlock.vue';
import AgentEditBlock from './ide/AgentEditBlock.vue';
import AgentImageBlock from './ide/AgentImageBlock.vue';
import IdeActivityIcon from './ide/IdeActivityIcon.vue';
import IdeAgentThreadStatusStrip from './ide/IdeAgentThreadStatusStrip.vue';
import { useConversationSeamScroll } from '../composables/useConversationSeamScroll';
import {
  isMarkdownFileAgentResponse,
  shouldHideAgentReportInThread,
  shouldUseAgentMarkdownBlock,
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
  prepareOperatorConversationDock,
  type ConversationDisplayItem,
} from '../lib/operator-conversation-view';
import { applyChatUiAction, type ChatUiAction } from '../lib/chat-ui-action';
import { operatorArtifactRecords } from '../lib/operator-artifact-view';
import {
  type OperatorThreadEntry,
  type ThreadMessageAttachment,
} from '../lib/operator-thread';
import {
  agentContentHasTranscriptBlocks,
  parseAgentTranscriptBlocks,
  thinkingPreview,
} from '../lib/agent-transcript-blocks';
import { sanitizeAgentThinkingForOperator } from '../lib/agent-live-line-view';
import { shouldShowAgentTerminalBackgroundControl } from '../lib/agent-terminal-background-view';
import { resolveChatAttachmentUrl } from '../api/control-plane';
import { threadAttachmentUrlForImagePath } from '../lib/thread-image-url';
import { useShellStore } from '../stores/shell';

const shell = useShellStore();
const conversationMessages = computed(() =>
  shell.layoutMode === 'ide' ? shell.threadMessages : shell.operatorThreadMessages,
);
const conversationDisplayItems = computed((): ConversationDisplayItem[] => {
  if (shell.layoutMode === 'ide') {
    return conversationMessages.value.map((message) => ({
      kind: 'message' as const,
      message,
    }));
  }
  return prepareOperatorConversationDock(conversationMessages.value, {
    artifacts: operatorArtifactRecords.value,
  }).items;
});

const conversationDockHint = computed(() =>
  shell.layoutMode === 'operator'
    ? 'Recent command results and VAXON artifacts. Run queue lives in Mission Control — not here.'
    : null,
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

function isMarkdownBlock(content: string, isComplete = true): boolean {
  return shouldUseAgentMarkdownBlock(content, isComplete) && !isErrorDump(content);
}

function isMarkdownFileBlock(content: string): boolean {
  return isMarkdownFileAgentResponse(content);
}

function shouldShowEditorStub(messageId: string, content: string): boolean {
  return Boolean(shell.agentReportEditorLink(messageId)) && shouldHideAgentReportInThread(content);
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

function hasTranscriptBlocks(content: string): boolean {
  return agentContentHasTranscriptBlocks(content);
}

function transcriptSegments(content: string) {
  return parseAgentTranscriptBlocks(content);
}

function segmentKey(messageId: string, index: number): string {
  return `${messageId}:${index}`;
}

function revealTerminalPanel(): void {
  shell.revealIdeTerminalPanel();
}

function backgroundAgentTerminalRun(): void {
  shell.backgroundIdeAgentRun();
}

function showTerminalBackgroundControl(messageId: string, segmentOpen: boolean): boolean {
  // Cursor shows "Run in Background" only on an in-flight shell card.
  return shouldShowAgentTerminalBackgroundControl({
    canStopIdeAgentRun: shell.canStopIdeAgentRun,
    terminalBlockRunning: segmentOpen && isStreamingMessage(messageId),
  });
}

function thinkingBodyText(text: string): string {
  return sanitizeAgentThinkingForOperator(text) || 'Thinking…';
}

async function copyTerminalOutput(output: string): Promise<void> {
  if (typeof navigator === 'undefined' || !navigator.clipboard || !output.trim()) {
    return;
  }
  await navigator.clipboard.writeText(output);
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

function displayItemKey(item: ConversationDisplayItem): string {
  if (item.kind === 'command_turn' || item.kind === 'dock_banner' || item.kind === 'artifact') {
    return item.messageId;
  }
  return item.message.message_id;
}

function attachmentUrlForImagePath(
  message: OperatorThreadEntry,
  path: string,
): string | null {
  return threadAttachmentUrlForImagePath(path, message.attachments ?? []);
}

function applyArtifactAction(action: { uiAction: ChatUiAction | null }): void {
  if (!action.uiAction) {
    return;
  }
  applyChatUiAction(shell, action.uiAction);
}

function messageImageAttachments(message: OperatorThreadEntry): ThreadMessageAttachment[] {
  return (message.attachments ?? []).filter((attachment) =>
    attachment.mime_type.startsWith('image/'),
  );
}

interface EnlargedAttachmentPreview {
  url: string;
  filename: string;
}

const enlargedAttachment = ref<EnlargedAttachmentPreview | null>(null);

function openAttachmentPreview(attachment: ThreadMessageAttachment): void {
  enlargedAttachment.value = {
    url: resolveChatAttachmentUrl(attachment.url),
    filename: attachment.filename,
  };
}

function closeAttachmentLightbox(): void {
  enlargedAttachment.value = null;
}

function handleAttachmentLightboxKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    closeAttachmentLightbox();
  }
}

function compactCommandSummary(output: string): string {
  const line = output.split('\n').map((part) => part.trim()).find(Boolean);
  if (!line) {
    return 'No output';
  }
  return line.length <= 96 ? line : `${line.slice(0, 93)}…`;
}

function restoreCommandToComposer(command: string): void {
  shell.restoreComposerDraft(command);
}

function isEmptyStreamingAgent(message: { role: string; message_id: string; content: string }): boolean {
  return message.role === 'agent' && !message.content.trim() && isStreamingMessage(message.message_id);
}

watch(
  conversationDisplayItems,
  () => {
    handleContentChange();
  },
  { immediate: true, deep: true },
);
</script>

<template>
  <div ref="rootRef" class="conversation-seam" @wheel.capture="handleWheel">
    <p v-if="conversationDockHint" class="conversation-seam__dock-hint">{{ conversationDockHint }}</p>
    <ul
      v-if="conversationDisplayItems.length"
      ref="listRef"
      class="conversation-seam__list"
    >
      <li
        v-for="item in conversationDisplayItems"
        :key="displayItemKey(item)"
        class="conversation-seam__item"
        :class="
          item.kind === 'dock_banner'
            ? 'conversation-seam__item--dock-banner'
            : item.kind === 'command_turn'
              ? 'conversation-seam__item--command-turn'
              : item.kind === 'artifact'
                ? 'conversation-seam__item--artifact'
              : `conversation-seam__item--${item.message.role}`
        "
      >
        <p v-if="item.kind === 'dock_banner'" class="conversation-seam__dock-banner">
          {{ item.text }}
        </p>

        <template v-else-if="item.kind === 'command_turn'">
          <div class="conversation-seam__meta">
            <div class="conversation-seam__meta-leading">
              <span class="conversation-seam__role">COMMAND</span>
              <span class="conversation-seam__command-label">{{ item.command }}</span>
              <span
                v-if="item.repeatCount && item.repeatCount > 1"
                class="conversation-seam__repeat-chip"
              >
                {{ item.repeatCount }}×
              </span>
              <span
                v-if="item.runId"
                class="conversation-seam__run-chip"
                :title="item.runId"
              >
                run {{ shortenRunId(item.runId) }}
              </span>
              <span
                class="conversation-seam__status-chip"
                :class="`conversation-seam__status-chip--${item.execution.status}`"
              >
                {{ item.execution.status }}
              </span>
            </div>
            <time class="conversation-seam__time" :datetime="item.createdAt">
              {{ formatThreadTimestamp(item.createdAt) }}
            </time>
          </div>
          <p
            v-if="item.compact"
            class="conversation-seam__content conversation-seam__content--command-compact"
          >
            Repeated {{ item.repeatCount }}× — showing latest {{ item.command }} only.
            {{ compactCommandSummary(item.execution.output) }}
          </p>
          <pre
            v-else-if="item.execution.output"
            class="conversation-seam__content conversation-seam__content--command-output"
          >{{ item.execution.output }}</pre>
          <p
            v-else
            class="conversation-seam__content conversation-seam__content--command-empty"
          >
            Command finished with no output.
          </p>
          <p
            v-if="item.execution.footer && !item.compact"
            class="conversation-seam__command-footer"
          >
            {{ item.execution.footer }}
          </p>
          <div class="conversation-seam__message-actions">
            <button
              type="button"
              class="conversation-seam__meta-icon-button conversation-seam__resend-button"
              title="Load this command back into the composer"
              aria-label="Resend"
              @click="restoreCommandToComposer(item.command)"
            >
              <span aria-hidden="true">↻</span>
            </button>
          </div>
        </template>

        <template v-else-if="item.kind === 'artifact'">
          <div class="conversation-seam__meta">
            <div class="conversation-seam__meta-leading">
              <span class="conversation-seam__role">ARTIFACT</span>
              <span class="conversation-seam__command-label">{{ item.artifact.title }}</span>
            </div>
            <time class="conversation-seam__time" :datetime="item.createdAt">
              {{ formatThreadTimestamp(item.createdAt) }}
            </time>
          </div>
          <p class="conversation-seam__content conversation-seam__content--artifact-summary">
            {{ item.artifact.summary }}
          </p>
          <pre class="conversation-seam__content conversation-seam__content--artifact-body">{{
            item.artifact.body
          }}</pre>
          <ul v-if="item.artifact.sources.length" class="conversation-seam__artifact-sources">
            <li v-for="source in item.artifact.sources" :key="`${item.artifact.artifactId}:${source.label}`">
              <strong>{{ source.label }}</strong>
              <span>{{ source.detail }}</span>
            </li>
          </ul>
          <div v-if="item.artifact.actions.length" class="conversation-seam__message-actions">
            <button
              v-for="action in item.artifact.actions"
              :key="`${item.artifact.artifactId}:${action.label}`"
              type="button"
              class="conversation-seam__meta-button"
              @click="applyArtifactAction(action)"
            >
              {{ action.label }}
            </button>
          </div>
        </template>

        <template v-else>
          <template v-if="item.message">
        <div class="conversation-seam__meta">
          <div class="conversation-seam__meta-leading">
            <span
              v-if="item.message.role === 'agent'"
              class="conversation-seam__role-icon"
              aria-label="Agent"
              title="Agent"
            >
              <IdeActivityIcon name="agent" :size="14" />
            </span>
            <span v-else class="conversation-seam__role">{{ formatThreadRole(item.message.role) }}</span>
          </div>
          <time class="conversation-seam__time" :datetime="item.message.created_at">
            {{ formatThreadTimestamp(item.message.created_at) }}
          </time>
        </div>

        <div
          v-if="messageImageAttachments(item.message).length"
          class="conversation-seam__attachments conversation-seam__attachments--thread"
          aria-label="Message attachments"
        >
          <button
            v-for="attachment in messageImageAttachments(item.message)"
            :key="attachment.attachment_id"
            type="button"
            class="conversation-seam__attachment-card conversation-seam__attachment-card--thread"
            :title="`Preview ${attachment.filename}`"
            @click="openAttachmentPreview(attachment)"
          >
            <img
              class="conversation-seam__attachment-preview"
              :src="resolveChatAttachmentUrl(attachment.url)"
              :alt="attachment.filename"
              loading="lazy"
            >
          </button>
        </div>

        <p
          v-if="item.message.role === 'system' && shouldCollapseSystemMessage(item.message.content) && !isSystemExpanded(item.message.message_id)"
          class="conversation-seam__content conversation-seam__content--system-collapsed"
        >
          {{ systemMessagePreview(item.message.content) }}
          <button
            type="button"
            class="conversation-seam__expand-toggle conversation-seam__expand-toggle--inline"
            @click="toggleSystemExpanded(item.message.message_id)"
          >
            Show
          </button>
        </p>

        <template v-else-if="item.message.role === 'system' && shouldCollapseSystemMessage(item.message.content)">
          <p class="conversation-seam__content">
            {{ item.message.content }}
          </p>
          <button
            type="button"
            class="conversation-seam__expand-toggle"
            @click="toggleSystemExpanded(item.message.message_id)"
          >
            Collapse
          </button>
        </template>

        <p
          v-else-if="item.message.role !== 'agent'"
          class="conversation-seam__content"
        >
          {{ item.message.content }}
        </p>

        <p
          v-else-if="isEmptyStreamingAgent(item.message)"
          class="conversation-seam__content conversation-seam__content--agent conversation-seam__content--typing"
        >
          <span class="conversation-seam__typing-dot" aria-hidden="true" />
          Agent is thinking…
        </p>

        <div
          v-else-if="hasTranscriptBlocks(item.message.content)"
          class="conversation-seam__blocks"
        >
          <template
            v-for="(segment, segmentIndex) in transcriptSegments(item.message.content)"
            :key="segmentKey(item.message.message_id, segmentIndex)"
          >
            <div
              v-if="segment.kind === 'thinking'"
              class="agent-block agent-block--thinking"
              :class="{ 'agent-block--thinking-live': segment.open && isStreamingMessage(item.message.message_id) }"
            >
              <button
                type="button"
                class="agent-block__thinking-toggle"
                @click="toggleThinking(segmentKey(item.message.message_id, segmentIndex), segment.open)"
              >
                <span class="agent-block__thinking-icon" aria-hidden="true">
                  {{ isThinkingExpanded(segmentKey(item.message.message_id, segmentIndex), segment.open) ? '▾' : '▸' }}
                </span>
                <span v-if="segment.open && isStreamingMessage(item.message.message_id)">
                  {{ segment.text.trim() ? thinkingPreview(segment.text, 120) : 'Thinking…' }}
                </span>
                <span v-else class="agent-block__thinking-preview">
                  Thought — {{ thinkingPreview(segment.text) }}
                </span>
              </button>
              <p
                v-if="isThinkingExpanded(segmentKey(item.message.message_id, segmentIndex), segment.open)"
                class="agent-block__thinking-body"
              >
                {{ thinkingBodyText(segment.text) }}
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
              :provider="segment.provider"
              :kind="segment.kindLabel"
              :live="segment.open && isStreamingMessage(item.message.message_id)"
            />

            <div v-else-if="segment.kind === 'terminal'" class="agent-block agent-block--terminal">
              <div class="agent-block__terminal-header">
                <button
                  type="button"
                  class="agent-block__terminal-reveal"
                  :title="`Open terminal panel for ${segment.command}`"
                  @click="revealTerminalPanel"
                >
                  <span class="agent-block__terminal-prompt" aria-hidden="true">$</span>
                  <code class="agent-block__terminal-command">{{ segment.command }}</code>
                  <span
                    v-if="segment.open && isStreamingMessage(item.message.message_id)"
                    class="agent-block__terminal-running"
                  >running…</span>
                </button>
                <button
                  v-if="showTerminalBackgroundControl(item.message.message_id, segment.open)"
                  type="button"
                  class="agent-block__terminal-background"
                  title="Move shell to terminal panel (vaxon)"
                  aria-label="Move shell command to background terminal"
                  @click="backgroundAgentTerminalRun"
                >
                  Background
                </button>
                <button
                  v-if="segment.output"
                  type="button"
                  class="agent-block__terminal-copy"
                  title="Copy terminal output"
                  @click="copyTerminalOutput(segment.output)"
                >
                  Copy
                </button>
              </div>
              <pre
                v-if="segment.output"
                class="agent-block__terminal-output"
              >{{ segment.output }}</pre>
            </div>

            <AgentEditBlock
              v-else-if="segment.kind === 'edit'"
              :path="segment.path"
              :added="segment.added"
              :removed="segment.removed"
              :diff="segment.diff"
              :open="segment.open"
            />

            <AgentImageBlock
              v-else-if="segment.kind === 'image'"
              :path="segment.path"
              :attachment-url="attachmentUrlForImagePath(item.message, segment.path)"
              :open="segment.open && isStreamingMessage(item.message.message_id)"
            />

            <div
              v-else-if="shouldShowEditorStub(item.message.message_id, segment.text)"
              class="conversation-seam__editor-stub"
            >
              <span class="conversation-seam__editor-stub-label">Opened in editor:</span>
              <button
                type="button"
                class="conversation-seam__editor-stub-link"
                @click="shell.focusAgentReportEditor(item.message.message_id)"
              >
                {{ shell.agentReportEditorLink(item.message.message_id)?.title }}
              </button>
            </div>

            <AgentFileReadBlock
              v-else-if="isMarkdownFileBlock(segment.text)"
              :content="segment.text"
            />

            <AgentMarkdownBlock
              v-else-if="isMarkdownBlock(segment.text, !isStreamingMessage(item.message.message_id))"
              :content="segment.text"
              :workspace-id="shell.currentWorkspace?.workspace_id ?? null"
            />

            <p
              v-else-if="segment.text.trim()"
              class="agent-block agent-block--text conversation-seam__content conversation-seam__content--agent"
            >
              {{ segment.text }}
            </p>
          </template>
          <span
            v-if="isStreamingMessage(item.message.message_id)"
            class="conversation-seam__stream-cursor"
            aria-hidden="true"
          >▍</span>
        </div>

        <template v-else-if="isErrorDump(item.message.content) && !isStreamingMessage(item.message.message_id)">
          <p class="conversation-seam__content conversation-seam__content--agent conversation-seam__content--error">
            {{ summarizeAgentErrorContent(item.message.content) }}
          </p>
          <button
            type="button"
            class="conversation-seam__expand-toggle"
            @click="toggleErrorExpanded(item.message.message_id)"
          >
            {{ isErrorExpanded(item.message.message_id) ? 'Hide details' : 'Show details' }}
          </button>
          <pre
            v-if="isErrorExpanded(item.message.message_id)"
            class="conversation-seam__content conversation-seam__content--agent conversation-seam__content--error-detail"
          >{{ item.message.content }}</pre>
        </template>

        <div
          v-else-if="shouldShowEditorStub(item.message.message_id, item.message.content)"
          class="conversation-seam__editor-stub"
        >
          <span class="conversation-seam__editor-stub-label">Opened in editor:</span>
          <button
            type="button"
            class="conversation-seam__editor-stub-link"
            @click="shell.focusAgentReportEditor(item.message.message_id)"
          >
            {{ shell.agentReportEditorLink(item.message.message_id)?.title }}
          </button>
        </div>

        <AgentFileReadBlock
          v-else-if="isMarkdownFileBlock(item.message.content)"
          :content="item.message.content"
        />

        <AgentMarkdownBlock
          v-else-if="isMarkdownBlock(item.message.content, !isStreamingMessage(item.message.message_id))"
          :content="item.message.content"
          :workspace-id="shell.currentWorkspace?.workspace_id ?? null"
        />

        <pre
          v-else-if="item.message.content.trim()"
          class="conversation-seam__content conversation-seam__content--agent"
          :class="{
            'conversation-seam__content--streaming': isStreamingMessage(item.message.message_id),
            'conversation-seam__content--streaming-full-access':
              isStreamingMessage(item.message.message_id) &&
              shell.ideComposerActivity?.executionAccess === 'full',
          }"
        >{{ item.message.content }}<span
          v-if="isStreamingMessage(item.message.message_id)"
          class="conversation-seam__stream-cursor"
          aria-hidden="true"
        >▍</span></pre>
        <div
          v-if="item.message.role === 'operator'"
          class="conversation-seam__message-actions"
        >
          <button
            type="button"
            class="conversation-seam__meta-icon-button conversation-seam__resend-button"
            title="Load this request back into the composer"
            aria-label="Resend"
            @click="restoreCommandToComposer(item.message.content)"
          >
            <span aria-hidden="true">↻</span>
          </button>
        </div>
          </template>
        </template>
      </li>
      <IdeAgentThreadStatusStrip v-if="shell.layoutMode === 'ide'" />
      <li
        v-else-if="showAgentWorking && !shell.agentStreamMessageId"
        class="conversation-seam__item conversation-seam__item--agent conversation-seam__item--typing"
        :class="{
          'conversation-seam__item--full-access':
            shell.ideComposerActivity?.executionAccess === 'full',
        }"
      >
        <div class="conversation-seam__meta">
          <div class="conversation-seam__meta-leading">
            <span class="conversation-seam__role-icon" aria-label="Agent" title="Agent">
              <IdeActivityIcon name="agent" :size="14" />
            </span>
            <span
              v-if="shell.ideComposerActivity?.executionAccess === 'full'"
              class="conversation-seam__access-chip conversation-seam__access-chip--full"
            >
              Full Access
            </span>
          </div>
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

  <Teleport to="body">
    <div
      v-if="enlargedAttachment"
      class="agent-dock-composer__image-lightbox"
      role="dialog"
      aria-modal="true"
      :aria-label="`Preview ${enlargedAttachment.filename}`"
      tabindex="-1"
      @click.self="closeAttachmentLightbox"
      @keydown="handleAttachmentLightboxKeydown"
    >
      <figure class="agent-dock-composer__image-lightbox-body">
        <img
          class="agent-dock-composer__image-lightbox-img"
          :src="enlargedAttachment.url"
          :alt="enlargedAttachment.filename"
        >
        <figcaption class="agent-dock-composer__image-lightbox-caption">
          {{ enlargedAttachment.filename }}
        </figcaption>
      </figure>
      <button
        type="button"
        class="agent-dock-composer__image-lightbox-close"
        aria-label="Close image preview"
        @click="closeAttachmentLightbox"
      >
        ×
      </button>
    </div>
  </Teleport>
</template>
