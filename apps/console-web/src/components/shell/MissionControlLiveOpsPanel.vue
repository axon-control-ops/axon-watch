<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';

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
  kairoLastRoutingReceipt,
} from '../../features/kairo-conversation/kairo-conversation-state';
import { useKairoConversation } from '../../features/kairo-conversation/use-kairo-conversation';
import KairoGalaxyOrb from '../../features/brain-galaxy/KairoGalaxyOrb.vue';
import { resolveGalaxyPresence } from '../../features/brain-galaxy/galaxy-presence-state';
import { projectLiveOperationsStream } from '../../features/brain-galaxy/live-operations-stream';
import { companyBusyEmployeesCount } from '../../features/workspace-agents/company-roster-busy';
import MissionControlAutonomyControl from './MissionControlAutonomyControl.vue';
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

const shell = useShellStore();
const { spokenText } = useSpokenUtteranceText();
const { pending, submitTurn, speechCapture } = useKairoConversation();
const reply = ref('');
const autonomyReceipts = ref<AutonomyReceipt[]>([]);
const autonomyEffective = ref(false);
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

const modeChip = computed(() => {
  if (presencePhase.value === 'speaking') return 'speaking';
  if (presencePhase.value === 'listening') return 'listening';
  if (presencePhase.value === 'autonomous' || fullAutonomyActive.value) return 'autonomous';
  return 'standby';
});

const liveBadge = computed(
  () =>
    shell.kairoSpeechActive ||
    presencePhase.value === 'listening' ||
    presencePhase.value === 'speaking' ||
    presencePhase.value === 'thinking' ||
    presencePhase.value === 'autonomous' ||
    fullAutonomyActive.value ||
    Boolean(shell.primaryActiveRun) ||
    companyBusyCount.value > 0 ||
    fleetActiveRuns.value > 0,
);

const micLive = computed(
  () => speechCapture.capturing.value && speechCapture.captureMode.value === 'manual',
);

const focusedWorkspaceLabel = computed(() => {
  const ws = shell.currentWorkspace;
  if (!ws) {
    return null;
  }
  return ws.display_name?.trim() || ws.workspace_id;
});

async function sendReply(content?: string): Promise<void> {
  const message = (content ?? reply.value).trim();
  if (!message || pending.value) {
    return;
  }
  if (content === 'yes' || content === 'not now') {
    markTransmissionAskAnswered(spokenLine.value);
  }
  reply.value = '';
  await submitTurn(message);
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

    <div
      class="mc-live-ops__orb-stage"
      :data-speaking="shell.kairoSpeechActive ? 'true' : 'false'"
      :data-mode="modeChip"
    >
      <KairoGalaxyOrb placement-mode="embedded" />
      <div class="mc-live-ops__orb-labels" aria-hidden="true">
        <p class="mc-live-ops__orb-name">{{ OPERATOR_PERSONA_NAME }}</p>
        <span class="mc-live-ops__orb-wave" />
        <p class="mc-live-ops__orb-tagline">{{ OPERATOR_PERSONA_OPS_TAGLINE }}</p>
      </div>
    </div>

    <MissionControlAutonomyControl />

    <article
      class="mc-transmission"
      :data-mode="transmission.mode"
      :aria-live="transmission.mode === 'transmitting' ? 'polite' : 'off'"
      aria-label="VAXON transmission"
    >
      <header class="mc-transmission__header">
        <span class="mc-transmission__pulse" aria-hidden="true" />
        <p class="mc-transmission__eyebrow">{{ transmission.eyebrow }}</p>
        <span class="mc-transmission__badge">{{ transmission.mode }}</span>
      </header>
      <p
        class="mc-transmission__body"
        :data-empty="transmission.empty ? 'true' : 'false'"
      >
        {{ transmission.body }}
      </p>
      <div v-if="asksForReply" class="mc-transmission__actions">
        <button type="button" :disabled="pending" @click="void sendReply('yes')">
          {{ affirmCta }}
        </button>
        <button type="button" :disabled="pending" @click="void sendReply('not now')">
          Not now
        </button>
      </div>
    </article>

    <div class="mc-live-ops__modes" role="status" aria-label="Voice mode">
      <span
        class="mc-live-ops__mode"
        :data-active="modeChip === 'speaking' ? 'true' : 'false'"
      >
        Speaking
      </span>
      <span
        class="mc-live-ops__mode"
        :data-active="modeChip === 'listening' ? 'true' : 'false'"
      >
        Listening
      </span>
      <span
        class="mc-live-ops__mode"
        :data-active="modeChip === 'autonomous' ? 'true' : 'false'"
      >
        Autonomous
      </span>
      <span
        class="mc-live-ops__mode"
        :data-active="modeChip === 'standby' ? 'true' : 'false'"
      >
        Standby
      </span>
    </div>

    <ul class="mc-live-ops__stream" aria-label="Live updates">
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

    <div class="mc-live-ops__reply">
      <form class="mc-live-ops__reply-form" @submit.prevent="void sendReply()">
        <button
          type="button"
          class="mc-live-ops__mic"
          :data-live="micLive ? 'true' : 'false'"
          :disabled="!speechCapture.supported || pending"
          :title="micLive ? 'Stop listening' : 'Talk to VAXON'"
          :aria-pressed="micLive"
          @click="toggleMic"
        >
          Mic
        </button>
        <input
          v-model="reply"
          type="text"
          autocomplete="off"
          :placeholder="`Talk to ${OPERATOR_PERSONA_NAME}… or REPORT`"
          :disabled="pending"
        >
        <span class="mc-live-ops__wave" aria-hidden="true">
          <i /><i /><i /><i /><i />
        </span>
        <button type="submit" class="mc-live-ops__send" :disabled="pending || !reply.trim()">
          {{ pending ? '…' : 'Send' }}
        </button>
      </form>
    </div>
  </section>
</template>

<style scoped src="./mission-control-live-ops.css"></style>
<style scoped src="./mission-control-transmission.css"></style>
