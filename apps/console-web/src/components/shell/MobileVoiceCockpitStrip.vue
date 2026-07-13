<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

import {
  voiceCockpitPresenceState,
  voiceCockpitStatusLine,
} from '../../features/voice-deck/voice-cockpit-presence';
import { isKairoVoiceSpeaking, subscribeKairoVoiceSpeaking } from '../../lib/kairo-voice-playback';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const speaking = ref(false);
let unsubscribeSpeaking: (() => void) | null = null;

const visible = computed(() => shell.mobileCompactLayout && shell.briefingLoadState === 'loaded');

const presence = computed(() => shell.operatorBriefing?.operator_presence ?? null);

const statusLine = computed(() => voiceCockpitStatusLine(presence.value));

const presenceState = computed(() => voiceCockpitPresenceState(presence.value));

function refreshSpeakingState(): void {
  speaking.value = isKairoVoiceSpeaking();
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
    class="mobile-voice-cockpit-strip"
    :class="`mobile-voice-cockpit-strip--${presenceState}`"
    aria-label="Mobile voice cockpit"
  >
    <span
      class="mobile-voice-cockpit-strip__pulse"
      :class="{ 'mobile-voice-cockpit-strip__pulse--active': speaking }"
      aria-hidden="true"
    />
    <div class="mobile-voice-cockpit-strip__copy">
      <p class="mobile-voice-cockpit-strip__label">{{ statusLine }}</p>
      <p class="mobile-voice-cockpit-strip__note">
        <a class="mobile-voice-cockpit-strip__mobile-link" href="/mobile">Open mobile shell</a>
        · Foreground voice · no background listening
      </p>
    </div>
  </aside>
</template>

<style scoped>
.mobile-voice-cockpit-strip {
  position: fixed;
  top: calc(var(--topbar-height) + var(--shell-gutter) + 0.25rem);
  left: var(--shell-gutter);
  right: var(--shell-gutter);
  z-index: 17;
  display: flex;
  align-items: center;
  gap: 0.55rem;
  padding: 0.4rem 0.65rem;
  border: 1px solid rgba(99, 102, 241, 0.28);
  border-radius: 0.45rem;
  background: rgba(10, 12, 22, 0.94);
  box-shadow: 0 0.2rem 0.85rem rgba(0, 0, 0, 0.24);
}

.mobile-voice-cockpit-strip--alerting {
  border-color: rgba(255, 120, 72, 0.42);
}

.mobile-voice-cockpit-strip--privacy_blocked {
  opacity: 0.82;
}

.mobile-voice-cockpit-strip__pulse {
  width: 0.48rem;
  height: 0.48rem;
  border-radius: 999px;
  background: rgba(99, 102, 241, 0.35);
  flex-shrink: 0;
}

.mobile-voice-cockpit-strip__pulse--active {
  background: rgba(0, 242, 255, 0.85);
  box-shadow: 0 0 0.4rem rgba(0, 242, 255, 0.4);
}

.mobile-voice-cockpit-strip__copy {
  min-width: 0;
}

.mobile-voice-cockpit-strip__label {
  margin: 0;
  font-size: 0.76rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mobile-voice-cockpit-strip__note {
  margin: 0.1rem 0 0;
  font-size: 0.64rem;
  opacity: 0.72;
}
</style>
