<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue';

import BootWakeOverlay from './components/BootWakeOverlay.vue';
import CenterWorkbench from './components/shell/CenterWorkbench.vue';
import IdeInterruptPanel from './components/ide/IdeInterruptPanel.vue';
import IdeVoiceStrip from './components/ide/IdeVoiceStrip.vue';
import LeftSidebar from './components/shell/LeftSidebar.vue';
import RightDock from './components/shell/RightDock.vue';
import StatusBar from './components/shell/StatusBar.vue';
import TopBar from './components/shell/TopBar.vue';
import VaultSurface from './components/vault/VaultSurface.vue';
import DataSurface from './components/data/DataSurface.vue';
import ScanHierarchyPreview from './dev/ScanHierarchyPreview.vue';
import { useAppSurface } from './composables/useAppSurface';
import { startLiveEventsSession } from './lib/live-events-session';
import { useIdeLayoutShortcuts } from './composables/useIdeLayoutShortcuts';
import { useVoiceDeckOnBoot } from './features/voice-deck/use-voice-deck';
import { useVoiceCockpitPresence } from './features/voice-deck/use-voice-cockpit-presence';
import MobileVoiceCockpitStrip from './components/shell/MobileVoiceCockpitStrip.vue';
import { useShellStore } from './stores/shell';

const shell = useShellStore();
useIdeLayoutShortcuts();
useVoiceDeckOnBoot();
useVoiceCockpitPresence();
let liveEventsSession: ReturnType<typeof startLiveEventsSession> | null = null;
const { appSurface } = useAppSurface();
const isVaultSurface = computed(() => appSurface.value === 'vault');
const isDataSurface = computed(() => appSurface.value === 'data');
const isFoundationSurface = computed(() => isVaultSurface.value || isDataSurface.value);
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
  appSurface,
  (surface, previous) => {
    if (surface === 'console' && (previous === 'vault' || previous === 'data')) {
      void shell.refreshRunSurfaces();
      void shell.loadWorkspaceFiles();
    }
  },
);

watch(
  bootComplete,
  (complete) => {
    if (!complete || showScanPreview.value) {
      shell.unbindViewportCompactListener();
      return;
    }

    shell.bindViewportCompactListener();

    liveEventsSession?.disconnect();
    liveEventsSession = startLiveEventsSession({
      onRefresh: () => shell.refreshRunSurfaces(),
      onPresenceRefresh: () => shell.refreshOperatorPresence(),
    });
  },
  { immediate: true },
);

watch(
  () => [bootComplete.value, shell.briefingLoadState] as const,
  ([complete, briefingState]) => {
    if (complete && briefingState === 'loaded') {
      void shell.maybeSpeakBootGreeting();
    }
  },
);

onUnmounted(() => {
  shell.unbindViewportCompactListener();
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
        'console-shell--ide': shell.layoutMode === 'ide',
        'console-shell--operator': shell.layoutMode === 'operator',
        'console-shell--brain-galaxy': shell.operatorBrainGalaxyActive,
        'console-shell--vault': isVaultSurface,
        'console-shell--data': isDataSurface,
      }"
      :data-layout-mode="shell.layoutMode"
    >
      <TopBar />
      <MobileVoiceCockpitStrip v-show="!isFoundationSurface" />
      <IdeInterruptPanel v-show="!isFoundationSurface" />
      <LeftSidebar v-show="!isFoundationSurface" />
      <VaultSurface v-show="isVaultSurface" />
      <DataSurface v-show="isDataSurface" />
      <CenterWorkbench v-show="!isFoundationSurface" />
      <RightDock v-show="!isFoundationSurface" />
      <StatusBar />
      <IdeVoiceStrip v-show="!isFoundationSurface" :foundation-surface="isFoundationSurface" />
    </div>
  </template>
</template>
