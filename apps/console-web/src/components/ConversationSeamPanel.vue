<script setup lang="ts">
import { ref } from 'vue';

import { useConversationSeamScroll } from '../composables/useConversationSeamScroll';
import {
  formatThreadTimestamp,
  shortenRunId,
} from '../lib/thread-message-view';
import type { OperatorThreadEntry } from '../lib/operator-thread';
import IdeActivityIcon from './ide/IdeActivityIcon.vue';
import IdeAgentThreadStatusStrip from './ide/IdeAgentThreadStatusStrip.vue';
import ConversationSeamHistoryNav from './conversation/ConversationSeamHistoryNav.vue';
import OperatorMessageActions from './conversation/OperatorMessageActions.vue';
import ConversationSeamAttachmentLightbox from './conversation/ConversationSeamAttachmentLightbox.vue';
import ConversationSeamMessageAttachments from './conversation/ConversationSeamMessageAttachments.vue';
import ConversationSeamArtifactBlock from './conversation/ConversationSeamArtifactBlock.vue';
import ConversationSeamThreadMessage from './conversation/ConversationSeamThreadMessage.vue';
import AgentDockStickyPrompt from './ide/agent-dock/AgentDockStickyPrompt.vue';
import { createConversationSeamAnswerBridge } from '../lib/conversation-seam-question-answers';
import { useConversationSeamPanel } from './conversation/useConversationSeamPanel';
import './ide/agent-dock/agent-dock-sticky-prompt.css';

const rootRef = ref<HTMLElement | null>(null);
const listRef = ref<HTMLElement | null>(null);
const { handleWheel, handleContentChange } = useConversationSeamScroll({
  rootRef,
  listRef,
  onContentChange: () => undefined,
});

const {
  shell,
  conversationDisplayItems,
  ideConversationTurns,
  ideMessageWindow,
  conversationDockHint,
  showAgentWorking,
  agentWorkingLabel,
  displayItemKey,
  applyArtifactAction,
  messageAttachments,
  enlargedAttachment,
  openAttachmentPreview,
  closeAttachmentLightbox,
  compactCommandSummary,
  showEarlierMessages,
  showNewerMessages,
  showLatestMessages,
} = useConversationSeamPanel(rootRef, listRef, handleContentChange);

const { answeredOptionForQuestion } = createConversationSeamAnswerBridge(conversationDisplayItems);

function flatIndexFor(message: OperatorThreadEntry): number {
  return conversationDisplayItems.value.findIndex(
    (item) => item.kind === 'message' && item.message.message_id === message.message_id,
  );
}
</script>
<template>
  <div ref="rootRef" class="conversation-seam" @wheel.capture="handleWheel">
    <p v-if="conversationDockHint" class="conversation-seam__dock-hint">{{ conversationDockHint }}</p>
    <ConversationSeamHistoryNav
      v-if="
        shell.layoutMode === 'ide' &&
        (ideMessageWindow.olderCount > 0 || ideMessageWindow.newerCount > 0)
      "
      :window="ideMessageWindow"
      @earlier="showEarlierMessages"
      @newer="showNewerMessages"
      @latest="showLatestMessages"
    />
    <ul
      v-if="conversationDisplayItems.length"
      ref="listRef"
      class="conversation-seam__list"
    >
      <template v-if="shell.layoutMode === 'ide'">
        <li
          v-for="turn in ideConversationTurns"
          :key="turn.id"
          class="conversation-seam__item conversation-seam__turn"
        >
          <div v-if="turn.prompt" class="conversation-seam__turn-prompt">
            <div class="conversation-seam__operator-turn">
              <AgentDockStickyPrompt :text="turn.prompt.content" show-resend>
                <template #attachments>
                  <ConversationSeamMessageAttachments
                    :attachments="messageAttachments(turn.prompt)"
                    @preview="openAttachmentPreview"
                  />
                </template>
              </AgentDockStickyPrompt>
            </div>
          </div>
          <div
            v-for="reply in turn.replies"
            :key="reply.message_id"
            class="conversation-seam__turn-reply"
          >
            <ConversationSeamThreadMessage
              :message="reply"
              :item-index="flatIndexFor(reply)"
              :answered-option-for-question="answeredOptionForQuestion"
              @preview="openAttachmentPreview"
            />
          </div>
        </li>
      </template>

      <template v-else>
        <li
          v-for="(item, itemIndex) in conversationDisplayItems"
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
            <OperatorMessageActions
              :text="item.command"
              edit-title="Edit — load this command into the composer"
              edit-aria-label="Edit command"
            />
          </template>

          <ConversationSeamArtifactBlock
            v-else-if="item.kind === 'artifact'"
            :artifact="item.artifact"
            :created-at="item.createdAt"
            :handoff-mutation-error="shell.handoffMutationError"
            @action="applyArtifactAction"
          />

          <template v-else-if="item.message">
            <div v-if="item.message.role === 'operator'" class="conversation-seam__operator-turn">
              <AgentDockStickyPrompt :text="item.message.content" show-resend>
                <template #attachments>
                  <ConversationSeamMessageAttachments
                    :attachments="messageAttachments(item.message)"
                    @preview="openAttachmentPreview"
                  />
                </template>
              </AgentDockStickyPrompt>
            </div>
            <ConversationSeamThreadMessage
              v-else
              :message="item.message"
              :item-index="itemIndex"
              :answered-option-for-question="answeredOptionForQuestion"
              @preview="openAttachmentPreview"
            />
          </template>
        </li>
      </template>

      <IdeAgentThreadStatusStrip v-if="shell.layoutMode === 'ide'" />
      <li
        v-else-if="showAgentWorking && !shell.agentStreamMessageId"
        class="conversation-seam__item conversation-seam__item--agent conversation-seam__item--typing"
        :class="{ 'conversation-seam__item--full-access': shell.ideComposerActivity?.executionAccess === 'full' }"
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
          :class="{ 'conversation-seam__content--typing-full-access': shell.ideComposerActivity?.executionAccess === 'full' }"
        >
          <span class="conversation-seam__typing-dot" aria-hidden="true" />
          {{ agentWorkingLabel }}
        </p>
      </li>
    </ul>
    <p v-else class="region-copy conversation-seam__empty">No active conversation</p>
  </div>

  <ConversationSeamAttachmentLightbox
    :attachment="enlargedAttachment"
    @close="closeAttachmentLightbox"
  />
</template>
