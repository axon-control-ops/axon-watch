<script setup lang="ts">
import { watch } from 'vue';

import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

// Mission Control LIVE OPERATIONS dock owns the embedded orb on operator layout.
// Keep the floating viewport orb off so mic/voice ownership stays single.
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
  <!-- Floating viewport orb disabled on operator — RightDock LIVE OPERATIONS hosts it. -->
  <span class="voice-orb-host-placeholder" hidden aria-hidden="true" />
</template>
