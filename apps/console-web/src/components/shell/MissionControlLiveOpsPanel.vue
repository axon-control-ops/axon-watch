<script setup lang="ts">
import { computed, ref } from 'vue';

import { useSpokenUtteranceText } from '../../composables/useSpokenUtteranceText';
import {
  OPERATOR_PERSONA_NAME,
  OPERATOR_PERSONA_OPS_TAGLINE,
} from '../../lib/operator-persona-name';
import {
  kairoConversationPhase,
  kairoLastRoutingReceipt,
} from '../../features/kairo-conversation/kairo-conversation-state';
import { useKairoConversation } from '../../features/kairo-conversation/use-kairo-conversation';
import KairoGalaxyOrb from '../../features/brain-galaxy/KairoGalaxyOrb.vue';
import { resolveGalaxyPresence } from '../../features/brain-galaxy/galaxy-presence-state';
import { projectLiveOperationsStream } from '../../features/brain-galaxy/live-operations-stream';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const { spokenText } = useSpokenUtteranceText();
const { pending, submitTurn, speechCapture } = useKairoConversation();
const reply = ref('');

const presence = computed(() =>
  resolveGalaxyPresence({
    selectedNodeId: null,
    selectedNodeKind: null,
    conversationPhase: kairoConversationPhase.value,
    speechCapturing: false,
    kairoSpeechActive: shell.kairoSpeechActive,
    agentStreamActive: shell.agentStreamActive,
    pendingApprovals:
      shell.runtimeSummary?.approvals.pending_count ??
      shell.operatorBriefing?.pending_approvals.count ??
      0,
    criticalSignals: shell.runtimeSummary?.signals.critical_count ?? 0,
    highSignals: shell.runtimeSummary?.signals.high_count ?? 0,
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
  }),
);

const spokenLine = computed(
  () => spokenText.value?.trim() || shell.operatorBriefing?.notice?.trim() || '',
);
const asksForReply = computed(() =>
  /\b(shall i|would you like me to|do you want me to|open attention for|want me to|triage)\b/i.test(
    spokenLine.value,
  ),
);

const modeChip = computed(() => {
  if (presencePhase.value === 'speaking') return 'speaking';
  if (presencePhase.value === 'listening') return 'listening';
  return 'standby';
});

const liveBadge = computed(
  () =>
    shell.kairoSpeechActive ||
    presencePhase.value === 'listening' ||
    presencePhase.value === 'speaking' ||
    Boolean(shell.primaryActiveRun),
);

const micLive = computed(
  () => speechCapture.capturing.value && speechCapture.captureMode.value === 'manual',
);

async function sendReply(content?: string): Promise<void> {
  const message = (content ?? reply.value).trim();
  if (!message || pending.value) {
    return;
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
</script>

<template>
  <section class="mc-live-ops" aria-label="VAXON live operations">
    <header class="mc-live-ops__header">
      <div class="mc-live-ops__title-row">
        <p class="mc-live-ops__eyebrow">Live operations</p>
        <span class="mc-live-ops__live" :data-live="liveBadge ? 'true' : 'false'">
          {{ liveBadge ? '● Live' : 'Standby' }}
        </span>
      </div>
    </header>

    <div
      class="mc-live-ops__orb-stage"
      :data-speaking="shell.kairoSpeechActive ? 'true' : 'false'"
      :data-mode="modeChip"
    >
      <KairoGalaxyOrb placement-mode="embedded" />
      <div class="mc-live-ops__orb-labels">
        <p class="mc-live-ops__orb-name">{{ OPERATOR_PERSONA_NAME }}</p>
        <p class="mc-live-ops__orb-tagline">{{ OPERATOR_PERSONA_OPS_TAGLINE }}</p>
      </div>
    </div>

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
      <p v-if="spokenLine && asksForReply" class="mc-live-ops__reply-line">{{ spokenLine }}</p>
      <div v-if="asksForReply" class="mc-live-ops__reply-actions">
        <button type="button" :disabled="pending" @click="void sendReply('yes')">
          Yes
        </button>
        <button type="button" :disabled="pending" @click="void sendReply('not now')">
          Not now
        </button>
      </div>
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
          :placeholder="`Talk to ${OPERATOR_PERSONA_NAME}…`"
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
