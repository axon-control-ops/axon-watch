<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';

import { useSpokenUtteranceText } from '../../composables/useSpokenUtteranceText';
import { OPERATOR_PERSONA_NAME } from '../../lib/operator-persona-name';
import {
  kairoConversationPhase,
  kairoConversationReply,
  kairoConversationThread,
  clearKairoConversationThread,
} from '../../features/kairo-conversation/kairo-conversation-state';
import { useKairoConversation } from '../../features/kairo-conversation/use-kairo-conversation';
import { formatVoiceGateFeedback } from '../../lib/kairo-voice-gate';
import { useMcVaxonPresence } from '../../composables/use-mc-vaxon-presence';
import MissionControlMachineCeoStrip from './MissionControlMachineCeoStrip.vue';
import McVaxonHeroBlock from './McVaxonHeroBlock.vue';
import VaxonSuperComposer from './VaxonSuperComposer.vue';
import { resolveVaxonTransmissionView } from '../../lib/mc-vaxon-transmission-view';
import {
  vaxonAffirmReplyCta,
  vaxonLineAsksForReply,
} from '../../lib/vaxon-reply-prompt';
import {
  isTransmissionAskAnswered,
  markTransmissionAskAnswered,
} from '../../lib/vaxon-transmission-reply-state';
import { useShellStore } from '../../stores/shell';

const props = withDefaults(
  defineProps<{
    layout?: 'dock' | 'center';
  }>(),
  {
    layout: 'dock',
  },
);

const shell = useShellStore();
const { spokenText } = useSpokenUtteranceText();
const { pending, submitTurn, speechCapture } = useKairoConversation();
const threadEl = ref<HTMLElement | null>(null);

const isCenterLayout = computed(() => props.layout === 'center');

const {
  autonomyMode,
  fullAutonomyActive,
  liveBadge,
  modeChip,
  presencePhase,
  streamItems,
} = useMcVaxonPresence();

const vaxonConversePending = computed(
  () => pending.value || kairoConversationPhase.value === 'thinking',
);

const fleetActivityActive = computed(
  () =>
    !vaxonConversePending.value &&
    (presencePhase.value === 'thinking' ||
      presencePhase.value === 'autonomous' ||
      Boolean(shell.primaryActiveRun)),
);

const transmission = computed(() =>
  resolveVaxonTransmissionView({
    spokenText: spokenText.value,
    conversationReply: kairoConversationReply.value,
    speaking:
      shell.kairoSpeechActive ||
      kairoConversationPhase.value === 'speaking' ||
      presencePhase.value === 'speaking',
    pending: vaxonConversePending.value,
  }),
);

const spokenLine = computed(() => transmission.value.body);

const asksForReply = computed(
  () =>
    vaxonLineAsksForReply(spokenLine.value) &&
    !transmission.value.empty &&
    !isTransmissionAskAnswered(spokenLine.value),
);
const affirmCta = computed(() => vaxonAffirmReplyCta(spokenLine.value));

const isTransmitting = computed(() => vaxonConversePending.value);

const hasThread = computed(() => kairoConversationThread.value.length > 0);

const focusedWorkspaceLabel = computed(() => {
  const ws = shell.currentWorkspace;
  if (!ws) {
    return null;
  }
  return ws.display_name?.trim() || ws.workspace_id;
});

const micLive = computed(
  () => speechCapture.capturing.value && speechCapture.captureMode.value === 'manual',
);

const speechCaptureError = computed(() => speechCapture.captureError.value);

const voiceGateFeedback = computed(() =>
  formatVoiceGateFeedback(
    speechCapture.lastGateReason.value,
    speechCapture.lastHeardTranscript.value,
    speechCapture.lastAccepted.value,
  ),
);

async function sendReply({
  content,
  submissionIntent = 'ask',
  attachments,
}: {
  content: string;
  submissionIntent?: 'ask' | 'dispatch';
  attachments?: import('../../lib/composer-clipboard-paste').ComposerClipboardImage[];
}): Promise<void> {
  const message = content.trim();
  if (!message && !attachments?.length) return;
  if (pending.value) return;
  if (message === 'yes' || message === 'not now') {
    markTransmissionAskAnswered(spokenLine.value);
  }
  const intent =
    message === 'yes' ? 'dispatch' : message === 'not now' ? 'ask' : submissionIntent;
  await submitTurn(message, { submissionIntent: intent, dockAttachments: attachments });
}

function toggleMic(): void {
  if (!speechCapture.supported) {
    return;
  }
  if (micLive.value) {
    speechCapture.stopCapture();
    return;
  }
  void speechCapture.startCapture('manual', { takeover: true });
}

watch(
  () => kairoConversationThread.value.length,
  () => void nextTick(() => {
    if (threadEl.value) {
      threadEl.value.scrollTop = threadEl.value.scrollHeight;
    }
  }),
);
</script>

<template>
  <section
    id="mission-control-live-ops"
    class="mc-live-ops"
    :class="{
      'mc-live-ops--busy': liveBadge,
      'mc-live-ops--transmitting': vaxonConversePending,
      'mc-live-ops--center': isCenterLayout,
      'mc-live-ops--thread-focus': isCenterLayout,
    }"
    aria-label="VAXON live operations"
  >
    <header v-if="!isCenterLayout" class="mc-live-ops__header">
      <div class="mc-live-ops__title-row">
        <p class="mc-live-ops__eyebrow">Live operations</p>
        <span class="mc-live-ops__live" :data-live="liveBadge ? 'true' : 'false'">
          {{ liveBadge ? '● Live' : 'Standby' }}
        </span>
      </div>
      <p v-if="focusedWorkspaceLabel" class="mc-live-ops__focus">
        Focus · {{ focusedWorkspaceLabel }}
      </p>
    </header>

    <template v-if="!isCenterLayout">
      <MissionControlMachineCeoStrip />

      <McVaxonHeroBlock
        :mode-chip="modeChip"
        :full-autonomy-active="fullAutonomyActive"
        :autonomy-mode="autonomyMode"
      />
    </template>

    <div
      class="mc-live-ops__scroll"
      :class="{ 'mc-live-ops__scroll--center': isCenterLayout }"
    >
      <article
        class="mc-transmission"
        :class="{ 'mc-transmission--thread-focus': isCenterLayout }"
        :data-mode="transmission.mode"
        :aria-live="isTransmitting ? 'polite' : 'off'"
        aria-label="VAXON transmission"
      >
        <header class="mc-transmission__header">
          <span class="mc-transmission__pulse" aria-hidden="true" />
          <p class="mc-transmission__eyebrow">{{ hasThread ? 'Conversation' : transmission.eyebrow }}</p>
          <div class="mc-transmission__header-actions">
            <span class="mc-transmission__badge">{{ transmission.mode }}</span>
            <button
              v-if="hasThread"
              type="button"
              class="mc-transmission__clear"
              title="Clear conversation"
              @click="clearKairoConversationThread()"
            >
              Clear
            </button>
          </div>
        </header>

        <div
          v-if="hasThread"
          ref="threadEl"
          class="mc-transmission__thread"
          aria-label="Conversation history"
        >
          <div
            v-for="(turn, i) in kairoConversationThread"
            :key="i"
            class="mc-transmission__turn"
            :data-role="turn.role"
          >
            <div class="mc-transmission__turn-meta">
              <span class="mc-transmission__turn-role">{{ turn.role === 'vaxon' ? OPERATOR_PERSONA_NAME : 'You' }}</span>
              <span class="mc-transmission__turn-at">{{ turn.at }}</span>
            </div>
            <p class="mc-transmission__turn-body">{{ turn.content }}</p>
          </div>

          <div v-if="isTransmitting" class="mc-transmission__turn mc-transmission__turn--thinking" data-role="vaxon">
            <div class="mc-transmission__turn-meta">
              <span class="mc-transmission__turn-role">{{ OPERATOR_PERSONA_NAME }}</span>
            </div>
            <p class="mc-transmission__thinking-dots">
              <span /><span /><span />
            </p>
          </div>
        </div>

        <div
          v-else
          class="mc-transmission__empty"
          :class="{ 'mc-transmission__empty--thread-focus': isCenterLayout }"
        >
          <p v-if="isTransmitting" class="mc-transmission__thinking-inline">
            <span class="mc-transmission__thinking-dots"><span /><span /><span /></span>
            {{ OPERATOR_PERSONA_NAME }} is working…
          </p>
          <template v-else-if="isCenterLayout">
            <p class="mc-transmission__empty-title">Conversation thread</p>
            <p v-if="fleetActivityActive" class="mc-transmission__fleet-note">
              Fleet run in progress — this channel opens when you command VAXON.
            </p>
            <p class="mc-transmission__empty-body">{{ transmission.body }}</p>
            <ul class="mc-transmission__empty-hints" aria-label="Suggested prompts">
              <li>Ask for status, routing, or a recommendation</li>
              <li>Type <strong>REPORT</strong> for a stand-up briefing</li>
              <li>Use <strong>Dispatch</strong> to assign work to the fleet</li>
            </ul>
          </template>
          <p v-else class="mc-transmission__empty-body">
            {{ transmission.body }}
          </p>
        </div>

        <div v-if="asksForReply" class="mc-transmission__actions">
          <button type="button" :disabled="pending" @click="void sendReply({ content: 'yes' })">
            {{ affirmCta }}
          </button>
          <button type="button" :disabled="pending" @click="void sendReply({ content: 'not now' })">
            Not now
          </button>
        </div>
      </article>

      <ul
        v-if="!isCenterLayout"
        class="mc-live-ops__stream"
        :class="{ 'mc-live-ops__stream--collapsed': isTransmitting }"
        aria-label="Live updates"
      >
        <li
          v-for="item in streamItems"
          :key="item.id"
          class="mc-live-ops__stream-item"
          :data-tone="item.tone"
          :data-kind="item.kind"
        >
          <span class="mc-live-ops__stream-at">{{ item.at }}</span>
          <span class="mc-live-ops__stream-agent">{{ item.agent }}</span>
          <span class="mc-live-ops__stream-text">{{ item.text }}</span>
        </li>
      </ul>
    </div>

    <VaxonSuperComposer
      v-if="isCenterLayout"
      layout="center"
      class="mc-live-ops__vaxon-composer"
      :pending="vaxonConversePending"
      :mic-live="micLive"
      :mic-supported="speechCapture.supported"
      :privacy-blocked="shell.operatorPresenceSettings.privacy_mode"
      :focused-workspace-label="focusedWorkspaceLabel"
      :capture-error="speechCaptureError"
      :voice-gate-feedback="voiceGateFeedback"
      @submit="void sendReply($event)"
      @toggle-mic="toggleMic"
    />
    <VaxonSuperComposer
      v-else
      layout="dock"
      :pending="vaxonConversePending"
      :mic-live="micLive"
      :mic-supported="speechCapture.supported"
      :privacy-blocked="shell.operatorPresenceSettings.privacy_mode"
      :focused-workspace-label="focusedWorkspaceLabel"
      :activity-label="shell.ideComposerActivity?.label ?? null"
      :activity-phase="presencePhase !== 'idle' ? presencePhase : null"
      :capture-error="speechCaptureError"
      :voice-gate-feedback="voiceGateFeedback"
      @submit="void sendReply($event)"
      @toggle-mic="toggleMic"
    />
  </section>
</template>

<style scoped src="./mission-control-live-ops.css"></style>
<style scoped src="./mission-control-transmission.css"></style>
