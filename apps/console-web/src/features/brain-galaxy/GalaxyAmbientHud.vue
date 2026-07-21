<script setup lang="ts">
/**
 * Ambient HUD kept for a11y live region only — no visible “Online / Continuous watch”
 * chips around the orb (movie-JARVIS minimal chrome).
 */
import { computed } from 'vue';

import type { GalaxyPresencePhase } from './galaxy-presence-state';

const props = defineProps<{
  presencePhase: GalaxyPresencePhase;
}>();

const spoken = computed(() => {
  switch (props.presencePhase) {
    case 'speaking':
      return 'VAXON speaking';
    case 'listening':
      return 'VAXON listening';
    case 'thinking':
      return 'VAXON working';
    case 'alerting':
      return 'VAXON attention';
    default:
      return 'VAXON ready';
  }
});
</script>

<template>
  <div class="galaxy-ambient-hud galaxy-ambient-hud--silent" aria-label="VAXON ambient activity">
    <p class="galaxy-ambient-hud__voice sr-only" aria-live="polite">{{ spoken }}</p>
  </div>
</template>

<style scoped>
.galaxy-ambient-hud--silent {
  pointer-events: none;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
