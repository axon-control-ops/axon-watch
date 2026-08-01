<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';

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
import { fetchMissionControlCriticalWork } from '../../features/mission-control/mission-control-ceo-api';
import MissionControlAutonomyControl from './MissionControlAutonomyControl.vue';
import MissionControlCeoCriticalStrip from './MissionControlCeoCriticalStrip.vue';
import MissionControlMachineCeoStrip from './MissionControlMachineCeoStrip.vue';
import { resolveVaxonTransmissionView } from '../../lib/mc-vaxon-transmission-view';
import {
  vaxonAffirmReplyCta,
  vaxonLineAsksForReply,
  vaxonLineNeedsIntervention,
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
const plateLoad = ref<'idle' | 'busy' | 'critical'>('idle');
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
const transmissionHasDetail = computed(() => transmission.value.detailLines.length > 0);
const showTransmissionCard = computed(
  () =>
    !transmission.value.empty ||
    transmission.value.mode === 'transmitting' ||
    presencePhase.value === 'thinking' ||
    presencePhase.value === 'speaking',
);

const asksForReply = computed(
  () =>
    vaxonLineAsksForReply(spokenLine.value) &&
    !transmission.value.empty &&
    !isTransmissionAskAnswered(spokenLine.value),
);
const needsIntervention = computed(
  () =>
    asksForReply.value ||
    (vaxonLineNeedsIntervention(spokenLine.value) && !transmission.value.empty),
);
const affirmCta = computed(() => vaxonAffirmReplyCta(spokenLine.value));

const modeChip = computed(() => {
  if (presencePhase.value === 'speaking') return 'speaking';
  if (presencePhase.value === 'listening') return 'listening';
  if (presencePhase.value === 'thinking') return 'listening';
  if (presencePhase.value === 'autonomous' || fullAutonomyActive.value) return 'autonomous';
  return 'standby';
});

/** Mode pills only while voice is live — hide after speaking ends (even if AUTO stays on). */
const showModeStrip = computed(
  () =>
    presencePhase.value === 'speaking' ||
    presencePhase.value === 'listening' ||
    presencePhase.value === 'thinking',
);

/** Reply CTAs stay only while speech is done and the ask is still unanswered. */
const showReplyActions = computed(
  () =>
    asksForReply.value &&
    !shell.kairoSpeechActive &&
    presencePhase.value !== 'speaking' &&
    presencePhase.value !== 'thinking',
);

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
  try {
    const pack = await fetchMissionControlCriticalWork(
      shell.currentWorkspace?.workspace_id ?? null,
    );
    const load = String(pack.plate?.load || 'idle');
    plateLoad.value =
      load === 'critical' || load === 'busy' ? load : 'idle';
    // #region agent log
    const stage = document.querySelector<HTMLElement>('.mc-live-ops__orb-stage');
    fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Debug-Session-Id': 'db8bb4',
      },
      body: JSON.stringify({
        sessionId: 'db8bb4',
        runId: 'inbox-orb-polish',
        hypothesisId: 'D',
        location: 'MissionControlLiveOpsPanel.vue:plate-load',
        message: 'Orb stage load applied',
        data: {
          plateLoad: plateLoad.value,
          waiting: pack.plate?.waiting ?? null,
          needsAttention: pack.plate?.needs_attention ?? null,
          stageHeight: stage?.offsetHeight ?? null,
          stageDataLoad: stage?.dataset.load ?? null,
        },
        timestamp: Date.now(),
      }),
    }).catch(() => {});
    // #endregion
  } catch {
    // Keep last plate load for orb scale.
  }
}

watch(
  () =>
    [
      showTransmissionCard.value,
      transmission.value.mode,
      asksForReply.value,
      showReplyActions.value,
      showModeStrip.value,
      presencePhase.value,
    ] as const,
  async () => {
    await Promise.resolve();
    // #region agent log
    const card = document.querySelector<HTMLElement>('.mc-transmission');
    const ops = document.querySelector<HTMLElement>('.mc-live-ops');
    fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Debug-Session-Id': 'db8bb4',
      },
      body: JSON.stringify({
        sessionId: 'db8bb4',
        runId: 'tx-hide-scroll',
        hypothesisId: 'S1',
        location: 'MissionControlLiveOpsPanel.vue:transmission-layout',
        message: 'Transmission chrome + scroll state',
        data: {
          visible: showTransmissionCard.value,
          mode: transmission.value.mode,
          presencePhase: presencePhase.value,
          asksForReply: asksForReply.value,
          showReplyActions: showReplyActions.value,
          showModeStrip: showModeStrip.value,
          actionsInHeader: Boolean(
            card?.querySelector('.mc-transmission__header .mc-transmission__actions'),
          ),
          modesInDom: Boolean(document.querySelector('.mc-live-ops__modes')),
          opsOverflowY: ops ? getComputedStyle(ops).overflowY : null,
          opsScrollH: ops?.scrollHeight ?? null,
          opsClientH: ops?.clientHeight ?? null,
          canScrollOps: ops ? ops.scrollHeight > ops.clientHeight + 2 : null,
        },
        timestamp: Date.now(),
      }),
    }).catch(() => {});
    // #endregion
  },
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

    <!-- Above the orb so CEO surfaces are never buried under Needs-you sheets. -->
    <MissionControlMachineCeoStrip />
    <MissionControlCeoCriticalStrip />

    <div
      class="mc-live-ops__orb-stage"
      :data-speaking="shell.kairoSpeechActive ? 'true' : 'false'"
      :data-mode="modeChip"
      :data-autonomy="fullAutonomyActive ? 'armed' : autonomyMode"
      :data-load="plateLoad"
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
      <article
        v-if="showTransmissionCard"
        class="mc-transmission"
        :data-mode="transmission.mode"
        :data-asking="asksForReply ? 'true' : 'false'"
        :data-needs-you="needsIntervention ? 'true' : 'false'"
        :aria-live="transmission.mode === 'transmitting' ? 'polite' : 'off'"
        aria-label="VAXON transmission"
      >
        <header class="mc-transmission__header">
          <span class="mc-transmission__pulse" aria-hidden="true" />
          <p class="mc-transmission__eyebrow">{{ transmission.eyebrow }}</p>
          <span
            v-if="showReplyActions || (needsIntervention && showModeStrip)"
            class="mc-transmission__badge mc-transmission__badge--needs-you"
          >
            Needs you
          </span>
          <span v-else class="mc-transmission__badge">{{ transmission.mode }}</span>
          <div v-if="showReplyActions" class="mc-transmission__actions">
            <button type="button" :disabled="pending" @click="void sendReply('yes')">
              {{ affirmCta }}
            </button>
            <button type="button" :disabled="pending" @click="void sendReply('not now')">
              Not now
            </button>
          </div>
        </header>
        <div
          class="mc-transmission__float"
          :data-live="transmission.mode === 'transmitting' ? 'true' : 'false'"
        >
          <p
            :key="transmission.summary"
            class="mc-transmission__body"
            :data-empty="transmission.empty ? 'true' : 'false'"
          >
            {{ transmission.summary }}
          </p>
          <ul v-if="transmissionHasDetail" class="mc-transmission__detail">
            <li v-for="(line, index) in transmission.detailLines" :key="index">
              {{ line }}
            </li>
          </ul>
        </div>
      </article>

      <div
        v-if="showModeStrip"
        class="mc-live-ops__modes"
        role="status"
        aria-label="Voice mode"
      >
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
    </div>

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
