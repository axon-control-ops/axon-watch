<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';

import {
  galaxyOrbHint,
  galaxyOrbModeClass,
  galaxyOrbModeLabel,
  galaxyOrbModelLabel,
  galaxyOrbStateClass,
  galaxyOrbStatusLabel,
  galaxyOrbTriggerAriaLabel,
} from './kairo-galaxy-orb-view';
import KairoGalaxyOrbChrome from './KairoGalaxyOrbChrome.vue';
import KairoGalaxyOrbDragHandle from './KairoGalaxyOrbDragHandle.vue';
import KairoGalaxyOrbFrame from './KairoGalaxyOrbFrame.vue';
import KairoGalaxyOrbSvg from './KairoGalaxyOrbSvg.vue';
import { useKairoGalaxyOrbDrag } from './use-kairo-galaxy-orb-drag';
import { useKairoGalaxyOrbPresence } from './use-kairo-galaxy-orb-presence';
import { useKairoGalaxyOrbVoice } from './use-kairo-galaxy-orb-voice';
import { createOrbTriggerGestureHandlers } from './orb-trigger-gestures';
import { resolveVoiceOrbPlacementApi } from './resolve-voice-orb-placement-api';
import { handleKairoGalaxyOrbInterrupt } from './kairo-galaxy-orb-interrupt';
import { useKairoGalaxyOrbChromeFlags } from './use-kairo-galaxy-orb-chrome-flags';
import { useKairoGalaxyOrbTtsBadge } from './use-kairo-galaxy-orb-tts-badge';
import { OPERATOR_PERSONA_NAME, OPERATOR_PERSONA_ORB_LABEL } from '../../lib/operator-persona-name';
import {
  kairoConversationPhase,
  kairoConversationReply,
} from '../kairo-conversation/kairo-conversation-state';
import { useShellStore } from '../../stores/shell';

const props = withDefaults(
  defineProps<{ placementMode?: 'viewport' | 'embedded' }>(),
  { placementMode: 'viewport' },
);

const personaOrbLabel = OPERATOR_PERSONA_ORB_LABEL;
const personaName = OPERATOR_PERSONA_NAME;
const shell = useShellStore();
const {
  voiceOrbPosition,
  voiceOrbUserPinned,
  voiceOrbDragging,
  voiceOrbAnchorStyle,
} = storeToRefs(shell);
const orbAnchor = ref<HTMLElement | null>(null);
const orbFrameRef = ref<{ rootEl: HTMLElement | null } | null>(null);
watch(
  () => orbFrameRef.value?.rootEl ?? null,
  (el) => { orbAnchor.value = el; },
  { immediate: true },
);

const {
  handsFreeEnabled,
  presenceState,
  speechCapture,
  gateFeedback,
  orbBusy,
  voiceBlocked,
} = useKairoGalaxyOrbPresence(shell);

const {
  kairoSpeaking,
  voiceBeat,
  handleOrbClick,
  handleOrbPointerDown,
  handleOrbPointerUp,
  cancelOrbPointerGesture,
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
  handleDragHandlePointerDown,
  handleLongPressPointerDown,
  handleOrbDragMove,
  finishOrbDrag,
  resetOrbPosition,
} = useKairoGalaxyOrbDrag({
  orbAnchor,
  replySignal,
  mode: props.placementMode,
  onDragEngaged: cancelOrbPointerGesture,
  placement: resolveVoiceOrbPlacementApi(
    props.placementMode,
    { voiceOrbPosition, voiceOrbUserPinned, voiceOrbDragging, voiceOrbAnchorStyle },
    {
      setVoiceOrbDock: shell.setVoiceOrbDock,
      setVoiceOrbPosition: shell.setVoiceOrbPosition,
      resetVoiceOrbDock: shell.resetVoiceOrbDock,
      requestVoiceOrbSmartDodge: shell.requestVoiceOrbSmartDodge,
      ensureVoiceOrbPosition: shell.ensureVoiceOrbPosition,
      persistVoiceOrbPlacement: shell.persistVoiceOrbPlacement,
    },
  ),
});

const { onTriggerPointerDown, onTriggerPointerMove, onTriggerPointerUp } =
  createOrbTriggerGestureHandlers(
    { handleOrbPointerDown, handleOrbPointerUp, cancelOrbPointerGesture },
    { handleLongPressPointerDown, handleOrbDragMove, finishOrbDrag },
  );

const speaking = computed(() => kairoSpeaking.value || shell.kairoSpeechActive);
const orbStateClass = computed(() =>
  galaxyOrbStateClass(
    presenceState.value,
    speaking.value,
    kairoConversationPhase.value,
    speechCapture.capturing.value,
    shell.agentStreamActive,
  ),
);
const orbModeClass = computed(() => galaxyOrbModeClass(handsFreeEnabled.value));
const modelLabel = computed(() => galaxyOrbModelLabel(shell.selectedComposerModel));
const hint = computed(() =>
  galaxyOrbHint(
    presenceState.value,
    speaking.value,
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
    speaking.value,
    speechCapture.capturing.value,
  ),
);
const triggerAriaLabel = computed(() =>
  galaxyOrbTriggerAriaLabel(personaName, voiceBlocked.value, handsFreeEnabled.value),
);
const { showInterrupt, showIdeClose } = useKairoGalaxyOrbChromeFlags({
  shell,
  placementMode: props.placementMode,
});
const ttsBadge = useKairoGalaxyOrbTtsBadge(speaking);
</script>

<template>
  <KairoGalaxyOrbFrame
    ref="orbFrameRef"
    :dragging="orbDragging"
    :placement-mode="placementMode"
    :chrome-live="showInterrupt"
    :ide-close="showIdeClose"
    :anchor-style="orbAnchorStyle"
    :persona-name="personaName"
    @hide="shell.hideVoiceOrb()"
  >
    <div
      class="kairo-galaxy-orb"
      :class="[
        orbStateClass,
        orbModeClass,
        {
          'kairo-galaxy-orb--ptt': speechCapture.capturing.value,
          'kairo-galaxy-orb--voice-live': speaking,
          'kairo-galaxy-orb--voice-beat': voiceBeat,
          'kairo-galaxy-orb--busy': orbBusy,
        },
      ]"
      :aria-label="`${personaName} voice orb`"
    >
      <KairoGalaxyOrbDragHandle
        v-if="placementMode === 'viewport'"
        @pointerdown="handleDragHandlePointerDown"
        @pointermove="handleOrbDragMove"
        @pointerup="finishOrbDrag"
        @pointercancel="finishOrbDrag"
      />

      <button
        type="button"
        class="kairo-galaxy-orb__trigger"
        :aria-disabled="voiceBlocked"
        :title="`Tap for hands-free · hold to talk · long-press to move · double-click to reset`"
        :aria-label="triggerAriaLabel"
        @click.stop="handleOrbClick"
        @dblclick.stop="resetOrbPosition"
        @pointerdown.prevent="onTriggerPointerDown"
        @pointermove="onTriggerPointerMove"
        @pointerup.prevent="onTriggerPointerUp"
        @pointercancel.prevent="onTriggerPointerUp"
      >
        <KairoGalaxyOrbSvg :persona-orb-label="personaOrbLabel" />
      </button>

      <KairoGalaxyOrbChrome
        :persona-name="personaName"
        :orb-status-label="orbStatusLabel"
        :mode-label="modeLabel"
        :tts-badge="ttsBadge"
        :show-interrupt="showInterrupt"
        :hint="hint"
        :model-label="modelLabel"
        @interrupt="handleKairoGalaxyOrbInterrupt(shell)"
        @focus-briefing="shell.focusKairoBriefing()"
      />
    </div>
  </KairoGalaxyOrbFrame>
</template>
