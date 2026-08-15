<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';

import {
  fetchAutonomyStatus,
  type AutonomyReceipt,
} from '../../api/autonomy-api';
import { useSpokenUtteranceText } from '../../composables/useSpokenUtteranceText';
import {
  OPERATOR_PERSONA_NAME,
  OPERATOR_PERSONA_OPS_TAGLINE,
} from '../../lib/operator-persona-name';
import {
  kairoConversationPhase,
  kairoConversationReply,
  kairoConversationThread,
  kairoLastRoutingReceipt,
  clearKairoConversationThread,
} from '../../features/kairo-conversation/kairo-conversation-state';
import { useKairoConversation } from '../../features/kairo-conversation/use-kairo-conversation';
import { formatVoiceGateFeedback } from '../../lib/kairo-voice-gate';
import KairoGalaxyOrb from '../../features/brain-galaxy/KairoGalaxyOrb.vue';
import { resolveGalaxyPresence } from '../../features/brain-galaxy/galaxy-presence-state';
import { projectLiveOperationsStream } from '../../features/brain-galaxy/live-operations-stream';
import { companyBusyEmployeesCount } from '../../features/workspace-agents/company-roster-busy';
import MissionControlAutonomyControl from './MissionControlAutonomyControl.vue';
import MissionControlMachineCeoStrip from './MissionControlMachineCeoStrip.vue';
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
import VaxonExecutiveComposer from './VaxonExecutiveComposer.vue';

const shell = useShellStore();
const { spokenText } = useSpokenUtteranceText();
const { pending, submitTurn, speechCapture } = useKairoConversation();
const autonomyReceipts = ref<AutonomyReceipt[]>([]);
const autonomyEffective = ref(false);
const threadEl = ref<HTMLElement | null>(null);
let autonomyPoll: ReturnType<typeof setInterval> | null = null;

const companyBusyCount = computed(() =>
  companyBusyEmployeesCount(shell.companyEmployeesFleet),
);
const fleetActiveRuns = computed(
  () =>
    shell.runtimeSummary?.active_runs?.length ??
    shell.operatorBriefing?.active_runs?.length ??
    0,
);

const autonomyMode = computed(
  () => shell.operatorPresenceSettings.autonomy_mode ?? 'manual',
);
const fullAutonomyActive = computed(
  () => autonomyMode.value === 'full' && autonomyEffective.value,
);

const presence = computed(() =>
  resolveGalaxyPresence({
    selectedNodeId: null,
    selectedNodeKind: null,
    conversationPhase: kairoConversationPhase.value,
    speechCapturing: false,
    kairoSpeechActive: shell.kairoSpeechActive,
    agentStreamActive: shell.agentStreamActive,
    companyBusyCount: companyBusyCount.value,
    fleetActiveRuns: fleetActiveRuns.value,
    pendingApprovals:
      shell.runtimeSummary?.approvals.pending_count ??
      shell.operatorBriefing?.pending_approvals.count ??
      0,
    criticalSignals: shell.runtimeSummary?.signals.critical_count ?? 0,
    highSignals: shell.runtimeSummary?.signals.high_count ?? 0,
    openSignals: shell.runtimeSummary?.signals.open_count ?? 0,
    fullAutonomyActive: fullAutonomyActive.value,
  }),
);

const presencePhase = computed(() => presence.value.phase);

const streamItems = computed(() =>
  projectLiveOperationsStream({
    briefing: shell.operatorBriefing,
    primaryActiveRun: shell.primaryActiveRun,
    employees: shell.companyEmployeesForCurrentWorkspace,
    presencePhase: presencePhase.value,
    routingReceipt: kairoLastRoutingReceipt.value,
    degradedReasons: [],
    autonomyReceipts: autonomyReceipts.value,
    autonomyMode: autonomyMode.value,
  }),
);

const transmission = computed(() =>
  resolveVaxonTransmissionView({
    spokenText: spokenText.value,
    conversationReply: kairoConversationReply.value,
    speaking: shell.kairoSpeechActive || presencePhase.value === 'speaking',
    pending: pending.value || presencePhase.value === 'thinking',
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

const isTransmitting = computed(
  () => transmission.value.mode === 'transmitting' || pending.value,
);

const hasThread = computed(() => kairoConversationThread.value.length > 0);

const modeChip = computed(() => {
  if (presencePhase.value === 'speaking') return 'speaking';
  if (presencePhase.value === 'listening') return 'listening';
  if (presencePhase.value === 'autonomous' || fullAutonomyActive.value) return 'autonomous';
  if (presencePhase.value === 'alerting') return 'scanning';
  return 'standby';
});

const liveBadge = computed(
  () =>
    shell.kairoSpeechActive ||
    presencePhase.value === 'listening' ||
    presencePhase.value === 'speaking' ||
    presencePhase.value === 'thinking' ||
    presencePhase.value === 'autonomous' ||
    presencePhase.value === 'alerting' ||
    fullAutonomyActive.value ||
    Boolean(shell.primaryActiveRun) ||
    companyBusyCount.value > 0 ||
    fleetActiveRuns.value > 0,
);

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

const focusedWorkspaceLabel = computed(() => {
  const ws = shell.currentWorkspace;
  if (!ws) {
    return null;
  }
  return ws.display_name?.trim() || ws.workspace_id;
});

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
  // Affirmative Needs-you answers must be allowed to trigger dig-in / handoff.
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

async function refreshAutonomyReceipts(): Promise<void> {
  try {
    const workspaceId = shell.currentWorkspace?.workspace_id?.trim();
    const feed = await fetchAutonomyStatus(workspaceId);
    if (feed.autonomy_mode !== shell.operatorPresenceSettings.autonomy_mode) {
      await shell.loadOperatorPresenceSettings({ reportError: false });
    }
    autonomyReceipts.value = feed.recent_receipts ?? [];
    autonomyEffective.value =
      feed.effective_autonomy &&
      feed.autonomy_mode === shell.operatorPresenceSettings.autonomy_mode;
  } catch {
    // Keep last good receipts; stream falls back to briefing items.
  }
}

watch(
  () => kairoConversationThread.value.length,
  () => void nextTick(() => {
    if (threadEl.value) {
      threadEl.value.scrollTop = threadEl.value.scrollHeight;
    }
  }),
);

onMounted(() => {
  void refreshAutonomyReceipts();
  autonomyPoll = setInterval(() => {
    void refreshAutonomyReceipts();
  }, 10_000);
});

onUnmounted(() => {
  if (autonomyPoll !== null) {
    clearInterval(autonomyPoll);
    autonomyPoll = null;
  }
});
</script>

<template>
  <section
    id="mission-control-live-ops"
    class="mc-live-ops"
    :class="{
      'mc-live-ops--busy': liveBadge,
      'mc-live-ops--transmitting': transmission.mode === 'transmitting',
    }"
    aria-label="VAXON live operations"
  >
    <header class="mc-live-ops__header">
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

    <!-- Above the orb so Machine CEO is never buried under Needs-you sheets. -->
    <MissionControlMachineCeoStrip />

    <div
      class="mc-live-ops__orb-stage"
      :data-speaking="shell.kairoSpeechActive ? 'true' : 'false'"
      :data-mode="modeChip"
      :data-autonomy="fullAutonomyActive ? 'armed' : autonomyMode"
    >
      <div class="mc-live-ops__orb-visual">
        <KairoGalaxyOrb placement-mode="embedded" />
        <div class="mc-live-ops__orb-labels" aria-hidden="true">
          <p class="mc-live-ops__orb-name">{{ OPERATOR_PERSONA_NAME }}</p>
          <span class="mc-live-ops__orb-wave" />
          <p class="mc-live-ops__orb-tagline">{{ OPERATOR_PERSONA_OPS_TAGLINE }}</p>
        </div>
        <MissionControlAutonomyControl />
      </div>
    </div>

    <div class="mc-live-ops__scroll">

      <!-- ── Conversation thread ─────────────────────────────────────────── -->
      <article
        class="mc-transmission"
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

        <!-- Thread view: full conversation history -->
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

          <!-- Thinking indicator -->
          <div v-if="isTransmitting" class="mc-transmission__turn mc-transmission__turn--thinking" data-role="vaxon">
            <div class="mc-transmission__turn-meta">
              <span class="mc-transmission__turn-role">{{ OPERATOR_PERSONA_NAME }}</span>
            </div>
            <p class="mc-transmission__thinking-dots">
              <span /><span /><span />
            </p>
          </div>
        </div>

        <!-- Empty state: no thread yet -->
        <div v-else class="mc-transmission__empty">
          <p v-if="isTransmitting" class="mc-transmission__thinking-inline">
            <span class="mc-transmission__thinking-dots"><span /><span /><span /></span>
            {{ OPERATOR_PERSONA_NAME }} is working…
          </p>
          <p v-else class="mc-transmission__empty-body">
            {{ transmission.body }}
          </p>
        </div>

        <!-- CTA buttons for yes/no prompts -->
        <div v-if="asksForReply" class="mc-transmission__actions">
          <button type="button" :disabled="pending" @click="void sendReply({ content: 'yes' })">
            {{ affirmCta }}
          </button>
          <button type="button" :disabled="pending" @click="void sendReply({ content: 'not now' })">
            Not now
          </button>
        </div>
      </article>

      <!-- ── Mode chips ──────────────────────────────────────────────────── -->
      <div class="mc-live-ops__modes" role="status" aria-label="Voice mode">
        <span class="mc-live-ops__mode" :data-active="modeChip === 'speaking' ? 'true' : 'false'">Speaking</span>
        <span class="mc-live-ops__mode" :data-active="modeChip === 'listening' ? 'true' : 'false'">Listening</span>
        <span class="mc-live-ops__mode" :data-active="modeChip === 'autonomous' ? 'true' : 'false'">Autonomous</span>
        <span class="mc-live-ops__mode" :data-active="modeChip === 'scanning' ? 'true' : 'false'">Scanning</span>
        <span class="mc-live-ops__mode" :data-active="modeChip === 'standby' ? 'true' : 'false'">Standby</span>
      </div>

      <!-- ── Live stream — collapses while VAXON is transmitting ──────────── -->
      <ul
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

    <VaxonExecutiveComposer
      :pending="pending"
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
