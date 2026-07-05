<script setup lang="ts">
import { onUnmounted, ref, watch } from 'vue';

import BootWakeOverlay from './components/BootWakeOverlay.vue';
import CenterWorkbench from './components/shell/CenterWorkbench.vue';
import LeftSidebar from './components/shell/LeftSidebar.vue';
import RightDock from './components/shell/RightDock.vue';
import StatusBar from './components/shell/StatusBar.vue';
import TopBar from './components/shell/TopBar.vue';
import ScanHierarchyPreview from './dev/ScanHierarchyPreview.vue';
import { startLiveEventsSession } from './lib/live-events-session';
import { useIdeLayoutShortcuts } from './composables/useIdeLayoutShortcuts';
import { useShellStore } from './stores/shell';

const shell = useShellStore();
useIdeLayoutShortcuts();
let liveEventsSession: ReturnType<typeof startLiveEventsSession> | null = null;
const showScanPreview = ref(
  typeof window !== 'undefined' &&
    import.meta.env.DEV &&
    new URLSearchParams(window.location.search).has('scan-preview'),
);

const bootComplete = ref(
  typeof window !== 'undefined' &&
    (window.matchMedia('(prefers-reduced-motion: reduce)').matches ||
      sessionStorage.getItem('axon-x-boot-complete') === '1'),
);

function completeBoot(): void {
  sessionStorage.setItem('axon-x-boot-complete', '1');
  bootComplete.value = true;
}

watch(
  bootComplete,
  (complete) => {
    if (!complete || showScanPreview.value) {
      return;
    }

    liveEventsSession?.disconnect();
    liveEventsSession = startLiveEventsSession({
      onRefresh: () => shell.refreshRunSurfaces(),
    });
  },
  { immediate: true },
);

onUnmounted(() => {
  liveEventsSession?.disconnect();
  liveEventsSession = null;
});
</script>

<template>
  <ScanHierarchyPreview v-if="showScanPreview" />

  <template v-else>
    <BootWakeOverlay v-if="!bootComplete" @complete="completeBoot" />

    <div
      v-show="bootComplete"
      class="console-shell console-shell--mockup"
      :class="{
        'dev-seams': shell.showDevSeams,
        'console-shell--mobile-compact': shell.mobileCompactLayout,
      }"
      :data-layout-mode="shell.layoutMode"
    >
      <TopBar />
      <LeftSidebar />
      <CenterWorkbench />
      <RightDock />
      <StatusBar />
    </div>
  </template>
</template>
