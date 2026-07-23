<script setup lang="ts">
import { watch } from 'vue';

import KairoGalaxyOrb from './KairoGalaxyOrb.vue';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

// Closing in IDE should not permanently lose the orb on operator return.
watch(
  () => shell.layoutMode,
  (mode, previous) => {
    if (previous === 'ide' && mode === 'operator') {
      shell.showVoiceOrb();
    }
  },
);
</script>

<template>
  <Teleport to="body">
    <!-- Floating orb is Operator-only — IDE already has mic/voice strip chrome. -->
    <KairoGalaxyOrb
      v-if="shell.voiceOrbVisible && shell.layoutMode !== 'ide' && shell.operatorBrainGalaxyActive"
      placement-mode="viewport"
    />
  </Teleport>
</template>
