<script setup lang="ts">
import { computed } from 'vue';

import {
  kairoAudioUnlockSnapshot,
  unlockKairoAudioPlayback,
} from '../../lib/kairo-audio-unlock';
import { spokenAlertPendingQueueSize } from '../../lib/spoken-alert-delivery';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

const needsUnlock = computed(() => {
  const settings = shell.operatorPresenceSettings;
  if (settings.privacy_mode || settings.kairo_narration === 'off') {
    return false;
  }
  if (
    !settings.spoken_alerts_enabled &&
    !settings.hands_free_enabled &&
    !settings.proactive_duplex_enabled
  ) {
    return false;
  }
  return !kairoAudioUnlockSnapshot.value.mediaUnlocked;
});

const queuedCount = computed(() => spokenAlertPendingQueueSize.value);

async function unlockNow(): Promise<void> {
  await unlockKairoAudioPlayback();
}
</script>

<template>
  <!-- Teleport out of the mockup CSS grid so an extra shell child cannot break layout. -->
  <Teleport to="body">
    <button
      v-if="needsUnlock"
      type="button"
      class="voice-unlock-banner"
      data-testid="voice-unlock-banner"
      @click="unlockNow"
    >
      <span class="voice-unlock-banner__label">Click or press a key to unlock voice</span>
      <span v-if="queuedCount > 0" class="voice-unlock-banner__queue">
        {{ queuedCount }} alert{{ queuedCount === 1 ? '' : 's' }} waiting
      </span>
    </button>
  </Teleport>
</template>

<style scoped>
.voice-unlock-banner {
  position: fixed;
  top: calc(var(--shell-gutter, 0.5rem) + var(--topbar-height, 3rem) + 0.35rem);
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  width: auto;
  max-width: min(36rem, calc(100vw - 2rem));
  margin: 0;
  padding: 0.4rem 0.9rem;
  border: 1px solid color-mix(in srgb, #2a6a9a 55%, transparent);
  border-radius: 999px;
  background: color-mix(in srgb, #0d1520 92%, #1a3a5c);
  color: color-mix(in srgb, #d7e0ea 88%, #9ec5ff);
  font: inherit;
  font-size: 0.72rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  cursor: pointer;
  z-index: 80;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}

.voice-unlock-banner:hover,
.voice-unlock-banner:focus-visible {
  background: color-mix(in srgb, #0d1520 80%, #245a8c);
  outline: none;
}

.voice-unlock-banner__queue {
  opacity: 0.75;
  text-transform: none;
  letter-spacing: 0;
}
</style>
