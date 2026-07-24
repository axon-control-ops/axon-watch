<script setup lang="ts">
import { nextTick, watch } from 'vue';

import KairoGalaxyOrb from './KairoGalaxyOrb.vue';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

function parkOrbClearOfMission(): void {
  if (shell.layoutMode !== 'operator' || !shell.voiceOrbVisible) {
    return;
  }
  // Force clear of fleet/task mosaic — center overlay is unusable.
  if (!shell.voiceOrbUserPinned) {
    shell.setVoiceOrbDock('top-right');
  }
  shell.requestVoiceOrbSmartDodge({ force: true });
}

// Closing in IDE should not permanently lose the orb on operator return.
watch(
  () => shell.layoutMode,
  (mode, previous) => {
    if (previous === 'ide' && mode === 'operator') {
      shell.showVoiceOrb();
    }
    if (mode === 'operator') {
      void nextTick(() => {
        window.setTimeout(parkOrbClearOfMission, 40);
      });
    }
  },
);

watch(
  () => shell.voiceOrbVisible,
  (visible) => {
    if (visible && shell.layoutMode === 'operator') {
      void nextTick(() => {
        window.setTimeout(parkOrbClearOfMission, 40);
      });
    }
  },
);
</script>

<template>
  <Teleport to="body">
    <!-- Floating orb is Operator-only — IDE already has mic/voice strip chrome. -->
    <KairoGalaxyOrb
      v-if="shell.voiceOrbVisible && shell.layoutMode !== 'ide'"
      placement-mode="viewport"
    />
  </Teleport>
</template>
