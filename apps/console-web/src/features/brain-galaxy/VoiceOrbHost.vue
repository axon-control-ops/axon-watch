<script setup lang="ts">
import { computed, nextTick, watch } from 'vue';

import KairoGalaxyOrb from './KairoGalaxyOrb.vue';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

/** Brain Graph owns the floating viewport orb; Mission Control uses the embedded LIVE OPS orb. */
const showFloatingOrb = computed(
  () =>
    shell.layoutMode === 'operator' &&
    shell.operatorBrainGalaxyActive &&
    shell.voiceOrbVisible,
);

function parkOrbForBrainGraph(): void {
  if (!showFloatingOrb.value) {
    return;
  }
  if (!shell.voiceOrbUserPinned) {
    shell.setVoiceOrbDock('bottom-left');
  }
  shell.requestVoiceOrbSmartDodge({ force: true, preferredDock: 'bottom-left' });
}

// Closing in IDE should not permanently lose the orb on operator return.
watch(
  () => shell.layoutMode,
  (mode, previous) => {
    if (previous === 'ide' && mode === 'operator') {
      shell.showVoiceOrb();
    }
  },
);

watch(
  showFloatingOrb,
  (visible) => {
    if (!visible) {
      return;
    }
    void nextTick(() => {
      window.setTimeout(parkOrbForBrainGraph, 40);
    });
  },
  { immediate: true },
);
</script>

<template>
  <Teleport to="body">
    <KairoGalaxyOrb
      v-if="showFloatingOrb"
      placement-mode="viewport"
    />
  </Teleport>
</template>
