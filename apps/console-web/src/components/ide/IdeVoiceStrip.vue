<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

import { kairoConversationPhase } from '../../features/kairo-conversation/kairo-conversation-state';
import {
  kairoCaptureLastAccepted,
  kairoCaptureLastGateReason,
  kairoCaptureLastHeard,
  kairoCaptureLastSubmitState,
} from '../../features/kairo-conversation/kairo-shared-speech-capture';
import {
  ideVoiceStripStatusLabel,
  shouldShowIdeVoiceStrip,
} from '../../lib/ide-voice-strip';
import { isKairoVoiceSpeaking, subscribeKairoVoiceSpeaking } from '../../lib/kairo-voice-playback';
import { useShellStore } from '../../stores/shell';

const props = withDefaults(
  defineProps<{
    foundationSurface?: boolean;
  }>(),
  { foundationSurface: false },
);

const shell = useShellStore();
const speaking = ref(false);
let unsubscribeSpeaking: (() => void) | null = null;

const visible = computed(() =>
  shouldShowIdeVoiceStrip({
    layoutMode: shell.layoutMode,
    settings: shell.operatorPresenceSettings,
    foundationSurface: props.foundationSurface,
    speaking: speaking.value || shell.kairoSpeechActive,
  }),
);

const statusLabel = computed(() =>
  ideVoiceStripStatusLabel({
    speaking: speaking.value || shell.kairoSpeechActive,
    narration: shell.operatorPresenceSettings.kairo_narration,
    liveLine: shell.kairoAgentLiveLine,
    conversationPhase: kairoConversationPhase.value,
  }),
);

const voiceDebugLine = computed(() => {
  const heard = kairoCaptureLastHeard.value.trim();
  const reason = kairoCaptureLastGateReason.value;
  const accepted = kairoCaptureLastAccepted.value;
  const submitState = kairoCaptureLastSubmitState.value;
  if (!heard && !reason && accepted === null && !submitState) {
    return '';
  }
  const parts = [];
  if (heard) {
    parts.push(`Heard: ${heard}`);
  }
  if (reason) {
    parts.push(`Gate: ${reason}`);
  }
  if (accepted !== null) {
    parts.push(`Accepted: ${accepted ? 'yes' : 'no'}`);
  }
  if (submitState) {
    parts.push(`Submit: ${submitState}`);
  }
  return parts.join(' · ');
});

const showStopSpeech = computed(() => shell.kairoSpeechActive);

function refreshSpeakingState(): void {
  speaking.value = isKairoVoiceSpeaking();
}

function disableStrip(): void {
  void shell.saveOperatorPresenceSettingsPatch({ ide_voice_strip_enabled: false });
}

function handleStopSpeech(): void {
  shell.stopKairoSpeech();
}

onMounted(() => {
  refreshSpeakingState();
  unsubscribeSpeaking = subscribeKairoVoiceSpeaking((active) => {
    speaking.value = active;
  });
});

onBeforeUnmount(() => {
  unsubscribeSpeaking?.();
});
</script>

<template>
  <aside
    v-if="visible"
    class="ide-voice-strip hud-panel-frame"
    aria-label="IDE voice strip"
  >
    <div class="ide-voice-strip__status">
      <span
        class="ide-voice-strip__pulse"
        :class="{ 'ide-voice-strip__pulse--active': speaking || shell.kairoSpeechActive }"
        aria-hidden="true"
      />
      <div class="ide-voice-strip__copy">
        <span class="ide-voice-strip__label">{{ statusLabel }}</span>
        <span v-if="voiceDebugLine" class="ide-voice-strip__debug">{{ voiceDebugLine }}</span>
      </div>
    </div>
    <div class="ide-voice-strip__actions">
      <button
        v-if="showStopSpeech"
        type="button"
        class="ide-voice-strip__stop"
        @click="handleStopSpeech"
      >
        Stop speaking
      </button>
      <button type="button" class="ide-voice-strip__close" @click="disableStrip">
        Hide voice strip
      </button>
    </div>
  </aside>
</template>

<style scoped>
.ide-voice-strip {
  position: fixed;
  left: var(--shell-gutter);
  right: var(--shell-gutter);
  bottom: calc(var(--statusbar-height) + var(--shell-gutter) + 0.35rem);
  z-index: 18;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.45rem 0.7rem;
  border: 1px solid rgba(99, 102, 241, 0.28);
  border-radius: 0.45rem;
  background: rgba(10, 12, 22, 0.94);
  box-shadow: 0 0.25rem 1rem rgba(0, 0, 0, 0.28);
}

.ide-voice-strip__status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.ide-voice-strip__copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.ide-voice-strip__pulse {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 999px;
  background: rgba(99, 102, 241, 0.35);
  flex-shrink: 0;
}

.ide-voice-strip__pulse--active {
  background: rgba(0, 242, 255, 0.85);
  box-shadow: 0 0 0.45rem rgba(0, 242, 255, 0.45);
  animation: ide-voice-strip-pulse 1.2s ease-in-out infinite;
}

.ide-voice-strip__label {
  font-size: 0.78rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  opacity: 0.92;
}

.ide-voice-strip__debug {
  font-size: 0.68rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  opacity: 0.7;
}

.ide-voice-strip__actions {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  flex-shrink: 0;
}

.ide-voice-strip__stop {
  border: 1px solid rgba(255, 140, 120, 0.42);
  border-radius: 0.35rem;
  background: rgba(255, 120, 72, 0.12);
  color: rgba(255, 210, 190, 0.96);
  cursor: pointer;
  font: inherit;
  font-size: 0.72rem;
  padding: 0.3rem 0.55rem;
}

.ide-voice-strip__close {
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 0.35rem;
  background: rgba(255, 255, 255, 0.04);
  color: inherit;
  cursor: pointer;
  font: inherit;
  font-size: 0.72rem;
  padding: 0.3rem 0.55rem;
}

@keyframes ide-voice-strip-pulse {
  0%,
  100% {
    opacity: 0.55;
  }
  50% {
    opacity: 1;
  }
}
</style>
