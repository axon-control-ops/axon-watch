<script setup lang="ts">
import { computed, ref } from 'vue';

import type { AgentQuestionOption } from '../../lib/agent-question-view';
import {
  formatThreadRole,
  formatThreadTimestamp,
  shouldCollapseSystemMessage,
  summarizeAgentErrorContent,
  systemMessagePreview,
  agentContentLooksLikeErrorDump,
  agentContentLooksLikeRuntimeFallback,
  threadMessageSpeakerLabel,
  threadMessageSpeakerStyle,
} from '../../lib/thread-message-view';
import { thinkingPreview, agentContentHasTranscriptBlocks } from '../../lib/agent-transcript-blocks';
import {
  isMarkdownFileAgentResponse,
  shouldHideAgentReportInThread,
  shouldUseAgentMarkdownBlock,
} from '../../lib/agent-message-markdown';
import { createTranscriptSegmentCache } from '../../lib/conversation-transcript-segment-cache';
import { sanitizeAgentThinkingForOperator, THINKING_SPEECH_FALLBACK } from '../../lib/agent-live-line-view';
import { prepareAgentTerminalOpen } from '../../lib/agent-terminal-open';
import {
  shouldShowAgentTerminalBackgroundControl,
  agentTerminalMirrorBadgeLabel,
} from '../../lib/agent-terminal-background-view';
import { armAgentShellMirror, agentShellMirrorActive } from '../../lib/agent-shell-mirror-state';
import { threadAttachmentUrlForImagePath } from '../../lib/thread-image-url';
import type { OperatorThreadEntry, ThreadMessageAttachment } from '../../lib/operator-thread';
import {
  agentReplyRegeneratePrompt,
  regenerateAgentReplyFromPrompt,
} from '../../lib/operator-message-composer-actions';
import { useShellStore } from '../../stores/shell';
import AgentMarkdownBlock from '../ide/AgentMarkdownBlock.vue';
import AgentFileReadBlock from '../ide/AgentFileReadBlock.vue';
import ConversationAgentStructuredBlock from '../ide/ConversationAgentStructuredBlock.vue';
import AgentEditBlock from '../ide/AgentEditBlock.vue';
import AgentImageBlock from '../ide/AgentImageBlock.vue';
import IdeActivityIcon from '../ide/IdeActivityIcon.vue';
import ConversationSeamTerminalBlock from './ConversationSeamTerminalBlock.vue';
import ConversationSeamMessageAttachments from './ConversationSeamMessageAttachments.vue';

const props = defineProps<{
  message: OperatorThreadEntry;
  itemIndex: number;
  /** YOU prompt that produced this agent reply — enables Cursor-style Regenerate. */
  precedingOperatorPrompt?: string | null;
  answeredOptionForQuestion: (
    messageId: string,
    prompt: string,
    options: AgentQuestionOption[],
    itemIndex: number,
  ) => AgentQuestionOption | null;
}>();

const emit = defineEmits<{
  preview: [attachment: ThreadMessageAttachment];
}>();

const shell = useShellStore();
const expandedErrorByMessageId = ref<Record<string, boolean>>({});
const expandedSystemByMessageId = ref<Record<string, boolean>>({});
const expandedThinkingKeys = ref<Record<string, boolean>>({});
const { transcriptSegments } = createTranscriptSegmentCache();
const regenerating = ref(false);

const regeneratePrompt = computed(() =>
  props.message.role === 'agent'
    ? agentReplyRegeneratePrompt(props.precedingOperatorPrompt)
    : null,
);

const regenerateDisabled = computed(
  () =>
    regenerating.value ||
    shell.commandMutationState === 'submitting' ||
    shell.agentStreamActive ||
    !regeneratePrompt.value,
);

function messageAttachments(message: OperatorThreadEntry): ThreadMessageAttachment[] {
  return message.attachments ?? [];
}

function isStreamingMessage(messageId: string): boolean {
  return shell.agentStreamActive && shell.agentStreamMessageId === messageId;
}

/** Only the newest shells in a turn get full cards — Lead OTA threads mint dozens. */
const RECENT_FULL_TERMINAL_CARDS = 6;

function isCompactTerminalCard(messageId: string, segmentIndex: number): boolean {
  const segments = transcriptSegments(
    messageId,
    props.message.content,
    isStreamingMessage(messageId),
  );
  const terminalIndexes = segments
    .map((segment, index) => (segment.kind === 'terminal' ? index : -1))
    .filter((index) => index >= 0);
  if (terminalIndexes.length <= RECENT_FULL_TERMINAL_CARDS) {
    return false;
  }
  const recent = new Set(terminalIndexes.slice(-RECENT_FULL_TERMINAL_CARDS));
  return !recent.has(segmentIndex);
}

async function onRegenerate(): Promise<void> {
  if (regenerateDisabled.value) {
    return;
  }
  regenerating.value = true;
  try {
    await regenerateAgentReplyFromPrompt(props.precedingOperatorPrompt);
  } finally {
    regenerating.value = false;
  }
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

function isRuntimeFallback(content: string): boolean {
  return agentContentLooksLikeRuntimeFallback(content);
}

function isErrorExpanded(messageId: string): boolean {
  return Boolean(expandedErrorByMessageId.value[messageId]);
}

function toggleErrorExpanded(messageId: string): void {
  expandedErrorByMessageId.value = {
    ...expandedErrorByMessageId.value,
    [messageId]: !expandedErrorByMessageId.value[messageId],
  };
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

function hasTranscriptBlocks(content: string): boolean {
  return agentContentHasTranscriptBlocks(content);
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

function thinkingBodyText(text: string): string {
  return sanitizeAgentThinkingForOperator(text) || THINKING_SPEECH_FALLBACK;
}

function isEmptyStreamingAgent(message: OperatorThreadEntry): boolean {
  return message.role === 'agent' && !message.content.trim() && isStreamingMessage(message.message_id);
}

function attachmentUrlForImagePath(message: OperatorThreadEntry, path: string): string | null {
  return threadAttachmentUrlForImagePath(path, message.attachments ?? []);
}

function revealTerminalPanel(segment: { command: string; output: string; open: boolean }): void {
  prepareAgentTerminalOpen(segment);
  void shell.backgroundIdeAgentRun();
}

function backgroundAgentTerminalRun(segment?: {
  command: string;
  output: string;
  open: boolean;
}): void {
  if (segment) {
    prepareAgentTerminalOpen(segment);
  } else {
    armAgentShellMirror();
  }
  void shell.backgroundIdeAgentRun();
}

function showTerminalBackgroundControl(messageId: string, segmentOpen: boolean): boolean {
  return shouldShowAgentTerminalBackgroundControl({
    canStopIdeAgentRun: shell.canStopIdeAgentRun,
    terminalBlockRunning: segmentOpen && isStreamingMessage(messageId),
  });
}

function terminalMirrorBadge(segmentOpen: boolean): string | null {
  return agentTerminalMirrorBadgeLabel({
    segmentOpen,
    mirrorActive: agentShellMirrorActive.value,
  });
}

type EmbeddedReportLine = { text: string; speaker: { name: string; role: string; employeeId: string } | null };

/** A Lead roll-up can contain several employee reports in one agent message.
 * Render those as real, colour-coded reporter blocks instead of hiding them
 * in Dana's plain text body. */
function embeddedReportLines(content: string): EmbeddedReportLine[] {
  const employees = shell.companyEmployeesForCurrentWorkspace ?? [];
  return content.split('\n').map((text) => {
    const explicit = text.match(/^\s*(?:[•*-]\s*)?(.+?)\s*\((lead|watcher|frontend|backend|integrations)\)\s*(?::|reported\b|completed\b|handoff\b)/i);
    const named = employees.find((employee) => {
      const name = String(employee.name ?? '').trim();
      return name && new RegExp(`^\\s*(?:[•*-]\\s*)?${name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*(?::|—|-)`, 'i').test(text);
    });
    const name = explicit?.[1]?.trim() || String(named?.name ?? '').trim();
    const role = explicit?.[2]?.toLowerCase() || String(named?.role ?? '').trim().toLowerCase();
    return { text, speaker: name && role ? { name, role, employeeId: String(named?.employee_id ?? `report:${name}:${role}`) } : null };
  });
}

function hasEmbeddedEmployeeReports(content: string): boolean {
  return embeddedReportLines(content).some((line) => line.speaker !== null);
}

async function copyTerminalOutput(output: string): Promise<void> {
  if (typeof navigator === 'undefined' || !navigator.clipboard || !output.trim()) {
    return;
  }
  await navigator.clipboard.writeText(output);
}
</script>

<template>
  <div class="conversation-seam__meta">
    <div class="conversation-seam__meta-leading">
      <span
        v-if="message.role === 'agent' || message.speaker_name"
        class="conversation-seam__speaker-chip"
        :style="threadMessageSpeakerStyle(message)"
        :aria-label="threadMessageSpeakerLabel(message)"
        :title="threadMessageSpeakerLabel(message)"
      >
        <IdeActivityIcon name="agent" :size="12" />
        <span>{{ threadMessageSpeakerLabel(message) }}</span>
      </span>
      <span v-else class="conversation-seam__role">{{ formatThreadRole(message.role) }}</span>
    </div>
    <time class="conversation-seam__time" :datetime="message.created_at">
      {{ formatThreadTimestamp(message.created_at) }}
    </time>
  </div>

  <ConversationSeamMessageAttachments
    :attachments="messageAttachments(message)"
    @preview="emit('preview', $event)"
  />

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
    :class="{ 'conversation-seam__content--operator': message.role === 'operator' }"
  >
    {{ message.content }}
  </p>

  <p
    v-else-if="isEmptyStreamingAgent(message)"
    class="conversation-seam__content conversation-seam__content--agent conversation-seam__content--typing"
    aria-label="Agent responding"
  >
    <span class="conversation-seam__typing-dot" aria-hidden="true" />
  </p>

  <div
    v-else-if="hasTranscriptBlocks(message.content)"
    class="conversation-seam__blocks"
  >
    <template
      v-for="(segment, segmentIndex) in transcriptSegments(
        message.message_id,
        message.content,
        isStreamingMessage(message.message_id),
      )"
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
          {{ thinkingBodyText(segment.text) }}
        </p>
      </div>

      <div v-else-if="segment.kind === 'tool'" class="agent-block agent-block--tool">
        <span class="agent-block__tool-dot" aria-hidden="true" />
        <span>{{ segment.label }}</span>
      </div>

      <ConversationAgentStructuredBlock
        v-else-if="
          segment.kind === 'plan' ||
          segment.kind === 'question' ||
          segment.kind === 'research' ||
          segment.kind === 'lead-fan-out' ||
          segment.kind === 'lead-standup'
        "
        :segment="segment"
        :workspace-id="shell.currentWorkspace?.workspace_id ?? null"
        :live="
          segment.kind !== 'plan' &&
          segment.kind !== 'lead-fan-out' &&
          segment.kind !== 'lead-standup' &&
          segment.open &&
          isStreamingMessage(message.message_id)
        "
        :message-id="message.message_id"
        :segment-index="segmentIndex"
        :answered-option="
          segment.kind === 'question'
            ? answeredOptionForQuestion(
              message.message_id,
              segment.prompt,
              segment.options,
              itemIndex,
            )
            : null
        "
      />

      <ConversationSeamTerminalBlock
        v-else-if="segment.kind === 'terminal'"
        :segment="segment"
        :message-id="message.message_id"
        :streaming="isStreamingMessage(message.message_id)"
        :compact="isCompactTerminalCard(message.message_id, segmentIndex)"
        :terminal-mirror-badge="terminalMirrorBadge"
        :show-terminal-background-control="showTerminalBackgroundControl" :agent-terminal-job-statuses="shell.agentTerminalJobStatuses"
        @reveal="revealTerminalPanel"
        @background="backgroundAgentTerminalRun"
        @copy-output="copyTerminalOutput"
      />

      <AgentEditBlock
        v-else-if="segment.kind === 'edit'"
        :path="segment.path"
        :added="segment.added"
        :removed="segment.removed"
        :diff="segment.diff"
        :open="segment.open"
      />

      <!-- Reproduce UI lives once in the sticky composer banner (avoid duplicate cards). -->
      <template v-else-if="segment.kind === 'debug-reproduce'"></template>

      <AgentImageBlock
        v-else-if="segment.kind === 'image'"
        :path="segment.path"
        :attachment-url="attachmentUrlForImagePath(message, segment.path)"
        :open="segment.open && isStreamingMessage(message.message_id)"
      />

      <div
        v-else-if="shouldShowEditorStub(message.message_id, segment.text)"
        class="conversation-seam__editor-stub"
      >
        <span class="conversation-seam__editor-stub-label">Opened in editor:</span>
        <button
          type="button"
          class="conversation-seam__editor-stub-link"
          @click="shell.focusAgentReportEditor(message.message_id)"
        >
          {{ shell.agentReportEditorLink(message.message_id)?.title }}
        </button>
      </div>

      <AgentFileReadBlock
        v-else-if="isMarkdownFileBlock(segment.text)"
        :content="segment.text"
      />

      <AgentMarkdownBlock
        v-else-if="isMarkdownBlock(segment.text, !isStreamingMessage(message.message_id))"
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
      v-if="isStreamingMessage(message.message_id)"
      class="conversation-seam__stream-cursor"
      aria-hidden="true"
    >0</span>
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

  <div
    v-else-if="shouldShowEditorStub(message.message_id, message.content)"
    class="conversation-seam__editor-stub"
  >
    <span class="conversation-seam__editor-stub-label">Opened in editor:</span>
    <button
      type="button"
      class="conversation-seam__editor-stub-link"
      @click="shell.focusAgentReportEditor(message.message_id)"
    >
      {{ shell.agentReportEditorLink(message.message_id)?.title }}
    </button>
  </div>

  <AgentFileReadBlock
    v-else-if="isMarkdownFileBlock(message.content)"
    :content="message.content"
  />

  <div
    v-else-if="hasEmbeddedEmployeeReports(message.content)"
    class="conversation-seam__embedded-reports conversation-seam__content--agent"
  >
    <div v-for="(line, index) in embeddedReportLines(message.content)" :key="`${message.message_id}:report:${index}`" class="conversation-seam__embedded-report-line">
      <span
        v-if="line.speaker"
        class="conversation-seam__speaker-chip"
        :style="threadMessageSpeakerStyle({ role: 'agent', speaker_name: line.speaker.name, speaker_role: line.speaker.role, speaker_employee_id: line.speaker.employeeId })"
      >
        <IdeActivityIcon name="agent" :size="12" />
        <span>{{ threadMessageSpeakerLabel({ role: 'agent', speaker_name: line.speaker.name, speaker_role: line.speaker.role }) }}</span>
      </span>
      <pre>{{ line.text }}</pre>
    </div>
  </div>

  <AgentMarkdownBlock
    v-else-if="isMarkdownBlock(message.content, !isStreamingMessage(message.message_id))"
    :content="message.content"
    :workspace-id="shell.currentWorkspace?.workspace_id ?? null"
  />

  <pre
    v-else-if="message.content.trim()"
    class="conversation-seam__content conversation-seam__content--agent"
    :class="{
      'conversation-seam__content--streaming': isStreamingMessage(message.message_id),
      'conversation-seam__content--streaming-full-access':
        isStreamingMessage(message.message_id) &&
        shell.ideComposerActivity?.executionAccess === 'full',
      'conversation-seam__content--runtime-fallback':
        !isStreamingMessage(message.message_id) && isRuntimeFallback(message.content),
    }"
  >{{ message.content }}<span
    v-if="isStreamingMessage(message.message_id)"
    class="conversation-seam__stream-cursor"
    aria-hidden="true"
  >▍</span></pre>

  <div
    v-if="regeneratePrompt && !isStreamingMessage(message.message_id)"
    class="conversation-seam__message-actions conversation-seam__message-actions--icons conversation-seam__agent-actions"
  >
    <button
      type="button"
      class="conversation-seam__meta-button conversation-seam__meta-button--icon conversation-seam__regenerate-button"
      title="Regenerate — run this turn again"
      aria-label="Regenerate reply"
      :disabled="regenerateDisabled"
      @click.stop="onRegenerate"
    >
      <svg
        class="conversation-seam__action-icon"
        width="14"
        height="14"
        viewBox="0 0 16 16"
        fill="none"
        stroke="currentColor"
        stroke-width="1.4"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path d="M3.1 6.2A5.1 5.1 0 0 1 12.4 5.4" />
        <path d="M12.9 9.8A5.1 5.1 0 0 1 3.6 10.6" />
        <path d="M12.4 2.85v2.7h-2.7" />
        <path d="M3.6 13.15v-2.7h2.7" />
      </svg>
    </button>
  </div>
</template>
