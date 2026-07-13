<script setup lang="ts">
import { computed, ref } from 'vue';

import {
  galaxyOrbHint,
  galaxyOrbModeClass,
  galaxyOrbModeLabel,
  galaxyOrbModelLabel,
  galaxyOrbStateClass,
  galaxyOrbStatusLabel,
} from './kairo-galaxy-orb-view';
import KairoGalaxyOrbSvg from './KairoGalaxyOrbSvg.vue';
import { useKairoGalaxyOrbDrag } from './use-kairo-galaxy-orb-drag';
import { useKairoGalaxyOrbVoice } from './use-kairo-galaxy-orb-voice';
import { resolveKairoPresenceState } from '../../lib/kairo-presence';
import { clearKairoVoiceFollowupWindow } from '../../lib/kairo-voice-followup-window';
import { formatVoiceGateFeedback } from '../../lib/kairo-voice-gate';
import { OPERATOR_PERSONA_NAME, OPERATOR_PERSONA_ORB_LABEL } from '../../lib/operator-persona-name';
import {
  isKairoConversationBusy,
  kairoConversationPhase,
  kairoConversationReply,
  setKairoConversationPhase,
} from '../kairo-conversation/kairo-conversation-state';
import { useKairoSpeechCapture } from '../kairo-conversation/use-kairo-speech-capture';
import { useShellStore } from '../../stores/shell';

const personaOrbLabel = OPERATOR_PERSONA_ORB_LABEL;
const personaName = OPERATOR_PERSONA_NAME;

const shell = useShellStore();
const orbAnchor = ref<HTMLElement | null>(null);

const pendingApprovals = computed(
  () =>
    shell.operatorBriefing?.pending_approvals.count ??
    shell.runtimeSummary?.approvals.pending_count ??
    0,
);

const handsFreeEnabled = computed(
  () => shell.operatorPresenceSettings.hands_free_enabled === true,
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

const speechCapture = useKairoSpeechCapture({
  privacyBlocked: () => shell.operatorPresenceSettings.privacy_mode,
  captureMode: 'manual',
  stopOnUnmount: 'manual_only',
});

const gateFeedback = computed(() =>
  formatVoiceGateFeedback(
    speechCapture.lastGateReason.value,
    speechCapture.lastHeardTranscript.value,
    speechCapture.lastAccepted.value,
  ),
);

const orbBusy = computed(() => isKairoConversationBusy());
const voiceBlocked = computed(() => shell.operatorPresenceSettings.privacy_mode);

const {
  kairoSpeaking,
  voiceBeat,
  handleOrbClick,
  handleOrbPointerDown,
  handleOrbPointerUp,
} = useKairoGalaxyOrbVoice({
  shell,
  speechCapture,
  voiceBlocked,
  orbBusy,
  handsFreeEnabled,
});

const replySignal = computed(
  () => `${kairoConversationReply.value ?? ''}|${kairoConversationPhase.value}`,
);

const {
  orbDragging,
  orbAnchorStyle,
  handleOrbDragStart,
  handleOrbDragMove,
  finishOrbDrag,
  resetOrbPosition,
} = useKairoGalaxyOrbDrag({
  orbAnchor,
  replySignal,
});

const orbStateClass = computed(() =>
  galaxyOrbStateClass(
    presenceState.value,
    kairoSpeaking.value || shell.kairoSpeechActive,
    kairoConversationPhase.value,
    speechCapture.capturing.value,
  ),
);

const orbModeClass = computed(() => galaxyOrbModeClass(handsFreeEnabled.value));
const modelLabel = computed(() => galaxyOrbModelLabel(shell.selectedComposerModel));

const hint = computed(() =>
  galaxyOrbHint(
    presenceState.value,
    kairoSpeaking.value || shell.kairoSpeechActive,
    kairoConversationPhase.value,
    handsFreeEnabled.value,
    gateFeedback.value,
  ),
);

const modeLabel = computed(() =>
  galaxyOrbModeLabel(handsFreeEnabled.value, kairoConversationPhase.value),
);

const orbStatusLabel = computed(() =>
  galaxyOrbStatusLabel(
    kairoConversationPhase.value,
    kairoSpeaking.value || shell.kairoSpeechActive,
    speechCapture.capturing.value,
  ),
);

const showInterrupt = computed(
  () => shell.kairoSpeechActive || kairoConversationPhase.value === 'thinking',
);

function handleInterrupt(): void {
  shell.interruptKairoVoice();
  clearKairoVoiceFollowupWindow();
  setKairoConversationPhase('idle');
}
</script>

<template>
  <div
    ref="orbAnchor"
    class="brain-galaxy-stage__jarvis-float"
    :class="{ 'brain-galaxy-stage__jarvis-float--dragging': orbDragging }"
    :style="orbAnchorStyle"
  >
    <button
      type="button"
      class="kairo-galaxy-orb__drag-handle"
      :title="`Drag to move ${personaName} · double-click to reset`"
      :aria-label="`Move ${personaName} orb`"
      @dblclick.stop="resetOrbPosition"
      @pointerdown.stop.prevent="handleOrbDragStart"
      @pointermove.stop.prevent="handleOrbDragMove"
      @pointerup.stop.prevent="finishOrbDrag"
      @pointercancel.stop.prevent="finishOrbDrag"
    >
      Move
    </button>

    <div
      class="kairo-galaxy-orb"
      :class="[
        orbStateClass,
        orbModeClass,
        {
          'kairo-galaxy-orb--ptt': speechCapture.capturing.value,
          'kairo-galaxy-orb--voice-live': kairoSpeaking || shell.kairoSpeechActive,
          'kairo-galaxy-orb--voice-beat': voiceBeat,
          'kairo-galaxy-orb--busy': orbBusy,
        },
      ]"
      :aria-label="`${personaName} voice orb`"
    >
      <button
        type="button"
        class="kairo-galaxy-orb__trigger"
        :disabled="voiceBlocked || !speechCapture.supported"
        :aria-label="
          voiceBlocked
            ? `${personaName} voice muted`
            : handsFreeEnabled
              ? `${personaName} hands-free — tap to switch to manual mode`
              : `${personaName} manual — tap for hands-free, hold to talk`
        "
        @click.stop="handleOrbClick"
        @pointerdown.prevent="handleOrbPointerDown"
        @pointerup.prevent="handleOrbPointerUp"
        @pointercancel.prevent="handleOrbPointerUp"
      >
        <KairoGalaxyOrbSvg :persona-orb-label="personaOrbLabel" />
      </button>

      <div class="kairo-galaxy-orb__status">
        <span class="kairo-galaxy-orb__status-dot" aria-hidden="true" />
        <span class="kairo-galaxy-orb__status-label">{{ orbStatusLabel }}</span>
      </div>

      <p v-if="modeLabel" class="kairo-galaxy-orb__mode-pill">{{ modeLabel }}</p>
      <button
        v-if="showInterrupt"
        type="button"
        class="kairo-galaxy-orb__interrupt"
        :title="`Stop ${personaName} (Esc)`"
        :aria-label="`Interrupt ${personaName}`"
        @click.stop="handleInterrupt"
      >
        Interrupt
      </button>
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
  </div>
</template>
