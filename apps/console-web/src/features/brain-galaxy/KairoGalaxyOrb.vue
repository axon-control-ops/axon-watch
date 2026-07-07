<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

import {
  galaxyOrbBeads,
  galaxyOrbHint,
  galaxyOrbModelLabel,
  galaxyOrbStateClass,
  galaxyOrbTicks,
} from './kairo-galaxy-orb-view';
import { kairoPresenceModuleParts } from '../../lib/mockup-shell-view';
import { resolveKairoPresenceState } from '../../lib/kairo-presence';
import { isSpeechQueueSpeaking } from '../../lib/speech-queue';
import { kairoConversationPhase } from '../kairo-conversation/kairo-conversation-state';
import { submitKairoConversationTranscript } from '../kairo-conversation/kairo-conversation-bus';
import { useKairoSpeechCapture } from '../kairo-conversation/use-kairo-speech-capture';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const speaking = ref(false);
let pollTimer: number | null = null;

const ticks = galaxyOrbTicks();
const beads = galaxyOrbBeads();

const pendingApprovals = computed(
  () =>
    shell.operatorBriefing?.pending_approvals.count ??
    shell.runtimeSummary?.approvals.pending_count ??
    0,
);

const presenceState = computed(() => {
  const highSignals =
    shell.operatorBriefing?.top_signals.filter((signal) => signal.severity === 'high').length ?? 0;
  const criticalSignals =
    shell.operatorBriefing?.top_signals.filter((signal) => signal.severity === 'critical').length ??
    0;
  return resolveKairoPresenceState({
    pendingApprovals: pendingApprovals.value,
    criticalSignals,
    highSignals,
    watchConnected: shell.runtimeSummary?.watch.connected ?? false,
    runtimeLoaded: shell.runtimeSummaryLoadState === 'loaded',
    privacyBlocked: shell.operatorPresenceSettings.privacy_mode,
  });
});

const parts = computed(() => kairoPresenceModuleParts(presenceState.value));
const orbClass = computed(() =>
  galaxyOrbStateClass(presenceState.value, speaking.value, kairoConversationPhase.value),
);
const modelLabel = computed(() => galaxyOrbModelLabel(shell.selectedComposerModel));
const hint = computed(() =>
  galaxyOrbHint(presenceState.value, speaking.value, kairoConversationPhase.value),
);

const voiceBlocked = computed(
  () =>
    shell.operatorPresenceSettings.privacy_mode ||
    shell.operatorPresenceSettings.kairo_narration === 'off' ||
    !shell.operatorPresenceSettings.spoken_alerts_enabled,
);

const speechCapture = useKairoSpeechCapture({
  privacyBlocked: () => shell.operatorPresenceSettings.privacy_mode,
  onFinalTranscript: submitKairoConversationTranscript,
});

function handleOrbPointerDown(): void {
  if (shell.operatorPresenceSettings.privacy_mode || !speechCapture.supported) {
    return;
  }
  speechCapture.startCapture();
}

function handleOrbPointerUp(): void {
  if (speechCapture.capturing.value) {
    speechCapture.stopCapture();
  }
}

function refreshSpeakingState(): void {
  speaking.value = isSpeechQueueSpeaking();
}

onMounted(() => {
  refreshSpeakingState();
  pollTimer = window.setInterval(refreshSpeakingState, 250);
});

onBeforeUnmount(() => {
  if (pollTimer !== null) {
    window.clearInterval(pollTimer);
  }
});
</script>

<template>
  <div
    class="brain-galaxy-stage__jarvis-float kairo-galaxy-orb"
    :class="[orbClass, { 'kairo-galaxy-orb--ptt': speechCapture.capturing.value }]"
    aria-label="KAIRO voice orb"
    @pointerdown.prevent="handleOrbPointerDown"
    @pointerup.prevent="handleOrbPointerUp"
    @pointerleave="handleOrbPointerUp"
  >
    <button
      type="button"
      class="kairo-galaxy-orb__trigger"
      :disabled="voiceBlocked"
      :aria-label="voiceBlocked ? 'KAIRO voice muted' : 'Speak operator briefing'"
      @pointerdown.stop
      @click="shell.speakOperatorBriefing()"
    >
      <svg
        class="kairo-galaxy-orb__svg"
        viewBox="0 0 200 200"
        role="img"
        aria-hidden="true"
      >
        <defs>
          <radialGradient id="kairo-orb-core-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stop-color="rgba(72, 196, 255, 0.28)" />
            <stop offset="100%" stop-color="rgba(72, 196, 255, 0)" />
          </radialGradient>
          <filter id="kairo-orb-glow" x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="2.4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <circle class="kairo-galaxy-orb__halo" cx="100" cy="100" r="92" fill="url(#kairo-orb-core-glow)" />

        <g class="kairo-galaxy-orb__ticks">
          <line
            v-for="(tick, index) in ticks"
            :key="index"
            :x1="tick.x1"
            :y1="tick.y1"
            :x2="tick.x2"
            :y2="tick.y2"
            :class="{ 'kairo-galaxy-orb__tick--major': tick.major }"
          />
        </g>

        <circle class="kairo-galaxy-orb__ring kairo-galaxy-orb__ring--outer" cx="100" cy="100" r="72" />
        <circle class="kairo-galaxy-orb__ring kairo-galaxy-orb__ring--dashed" cx="100" cy="100" r="66" />
        <path
          class="kairo-galaxy-orb__arc"
          d="M 44 100 A 66 66 0 0 1 62 56"
          pathLength="100"
        />

        <g class="kairo-galaxy-orb__beads">
          <circle
            v-for="(bead, index) in beads"
            :key="index"
            class="kairo-galaxy-orb__bead"
            :cx="bead.cx"
            :cy="bead.cy"
            r="2.6"
          />
        </g>

        <circle class="kairo-galaxy-orb__ring kairo-galaxy-orb__ring--inner" cx="100" cy="100" r="54" />
        <circle class="kairo-galaxy-orb__ring kairo-galaxy-orb__ring--core" cx="100" cy="100" r="46" />

        <text class="kairo-galaxy-orb__core-text" x="100" y="104">KAIRO</text>

        <circle class="kairo-galaxy-orb__beacon" cx="34" cy="34" r="4.5" filter="url(#kairo-orb-glow)" />
        <circle class="kairo-galaxy-orb__sweep" cx="100" cy="100" r="48" />
      </svg>
    </button>

    <div class="kairo-galaxy-orb__status">
      <span class="kairo-galaxy-orb__status-dot" aria-hidden="true" />
      <span class="kairo-galaxy-orb__status-label">{{ parts.subtitle }}</span>
    </div>

    <p class="kairo-galaxy-orb__hint">{{ hint }}</p>

    <button
      type="button"
      class="kairo-galaxy-orb__model"
      @pointerdown.stop
      @click="shell.focusKairoBriefing()"
    >
      <span aria-hidden="true">◆</span>
      {{ modelLabel }}
    </button>
  </div>
</template>
