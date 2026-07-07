<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

import {
  ideVoiceStripStatusLabel,
  shouldShowIdeVoiceStrip,
} from '../../lib/ide-voice-strip';
import { isSpeechQueueSpeaking } from '../../lib/speech-queue';
import { useShellStore } from '../../stores/shell';

const props = withDefaults(
  defineProps<{
    foundationSurface?: boolean;
  }>(),
  { foundationSurface: false },
);

const shell = useShellStore();
const speaking = ref(false);
let pollTimer: number | null = null;

const visible = computed(() =>
  shouldShowIdeVoiceStrip({
    layoutMode: shell.layoutMode,
    settings: shell.operatorPresenceSettings,
    foundationSurface: props.foundationSurface,
  }),
);

const statusLabel = computed(() =>
  ideVoiceStripStatusLabel({
    speaking: speaking.value,
    narration: shell.operatorPresenceSettings.kairo_narration,
    liveLine: shell.kairoAgentLiveLine,
  }),
);

function refreshSpeakingState(): void {
  speaking.value = isSpeechQueueSpeaking();
}

function disableStrip(): void {
  void shell.saveOperatorPresenceSettingsPatch({ ide_voice_strip_enabled: false });
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
  <aside
    v-if="visible"
    class="ide-voice-strip hud-panel-frame"
    aria-label="IDE voice strip"
  >
    <div class="ide-voice-strip__status">
      <span
        class="ide-voice-strip__pulse"
        :class="{ 'ide-voice-strip__pulse--active': speaking }"
        aria-hidden="true"
      />
      <span class="ide-voice-strip__label">{{ statusLabel }}</span>
    </div>
    <button type="button" class="ide-voice-strip__close" @click="disableStrip">
      Hide voice strip
    </button>
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

.ide-voice-strip__close {
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 0.35rem;
  background: rgba(255, 255, 255, 0.04);
  color: inherit;
  cursor: pointer;
  font: inherit;
  font-size: 0.72rem;
  padding: 0.3rem 0.55rem;
  flex-shrink: 0;
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
