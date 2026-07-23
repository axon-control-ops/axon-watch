<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue';

import BootWakeOverlay from './components/BootWakeOverlay.vue';
import CenterWorkbench from './components/shell/CenterWorkbench.vue';
import LeftSidebar from './components/shell/LeftSidebar.vue';
import RightDock from './components/shell/RightDock.vue';
import StatusBar from './components/shell/StatusBar.vue';
import TopBar from './components/shell/TopBar.vue';
import VaultSurface from './components/vault/VaultSurface.vue';
import DataSurface from './components/data/DataSurface.vue';
import SkillsSurface from './components/skills/SkillsSurface.vue';
import OperatorMobileShell from './components/shell/OperatorMobileShell.vue';
import OperatorSettingsSurface from './components/settings/OperatorSettingsSurface.vue';
import ScanHierarchyPreview from './dev/ScanHierarchyPreview.vue';
import { useAppSurface } from './composables/useAppSurface';
import { startLiveEventsSession } from './lib/live-events-session';
import { useIdeLayoutShortcuts } from './composables/useIdeLayoutShortcuts';
import { useIdeKairoInterrupt } from './composables/useIdeKairoInterrupt';
import { useVoiceDeckOnBoot } from './features/voice-deck/use-voice-deck';
import { useVoiceCockpitPresence } from './features/voice-deck/use-voice-cockpit-presence';
import { useKairoAppVoice } from './features/kairo-conversation/use-kairo-app-voice';
import MobileVoiceCockpitStrip from './components/shell/MobileVoiceCockpitStrip.vue';
import VoiceOrbHost from './features/brain-galaxy/VoiceOrbHost.vue';
import HudHoloAtmosphere from './features/hud-holo/HudHoloAtmosphere.vue';
import { useShellStore } from './stores/shell';

const shell = useShellStore();
useIdeLayoutShortcuts();
useIdeKairoInterrupt();
useVoiceDeckOnBoot();
useVoiceCockpitPresence();
useKairoAppVoice();
let liveEventsSession: ReturnType<typeof startLiveEventsSession> | null = null;
const { appSurface } = useAppSurface();
const isVaultSurface = computed(() => appSurface.value === 'vault');
const isDataSurface = computed(() => appSurface.value === 'data');
const isSkillsSurface = computed(() => appSurface.value === 'skills');
const isMobileSurface = computed(() => appSurface.value === 'mobile');
const isSettingsSurface = computed(() => appSurface.value === 'settings');
const isFoundationSurface = computed(
  () =>
    isVaultSurface.value ||
    isDataSurface.value ||
    isSkillsSurface.value ||
    isMobileSurface.value ||
    isSettingsSurface.value,
);
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
    if (
      surface === 'console' &&
      (previous === 'vault' ||
        previous === 'data' ||
        previous === 'skills' ||
        previous === 'settings' ||
        previous === 'mobile')
    ) {
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

    // #region agent log
    requestAnimationFrame(() => {
      const root = document.querySelector('.console-shell--mockup');
      if (!(root instanceof HTMLElement)) {
        return;
      }
      const style = getComputedStyle(root);
      fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Debug-Session-Id': 'fc0b35',
        },
        body: JSON.stringify({
          sessionId: 'fc0b35',
          runId: 'post-fix',
          hypothesisId: 'H-holo-hud',
          location: 'App.vue:bootComplete',
          message: 'holographic glass3d shell armed',
          data: {
            hasGlass3d: root.classList.contains('console-shell--glass3d'),
            dataHud: root.getAttribute('data-hud'),
            perspective: style.perspective,
            layoutMode: shell.layoutMode,
            accentSample: getComputedStyle(root).getPropertyValue('--accent-brand').trim(),
            textHud: getComputedStyle(root).getPropertyValue('--text-hud').trim(),
            surfaceShell: getComputedStyle(root).getPropertyValue('--surface-shell').trim(),
          },
          timestamp: Date.now(),
        }),
      }).catch(() => {});
    });
    // #endregion

    liveEventsSession?.disconnect();
    liveEventsSession = startLiveEventsSession({
      onRefresh: () => {
        // IDE must stay interactive: skip heavy operator surface refresh while
        // coding/streaming. Operator layout still needs light run refresh.
        if (shell.layoutMode === 'ide') {
          return;
        }
        return shell.refreshRunSurfaces({ light: true });
      },
      onPresenceRefresh: () => {
        if (shell.layoutMode === 'ide') {
          return;
        }
        return shell.refreshOperatorPresence();
      },
      onSpokenBriefing: () => shell.speakOperatorBriefing(),
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
        'console-shell--brain-galaxy':
          shell.layoutMode === 'operator' && shell.operatorBrainGalaxyActive,
        'console-shell--glass3d': !isFoundationSurface,
        'console-shell--vault': isVaultSurface,
        'console-shell--data': isDataSurface,
        'console-shell--skills': isSkillsSurface,
        'console-shell--mobile': isMobileSurface,
        'console-shell--settings': isSettingsSurface,
      }"
      :data-layout-mode="shell.layoutMode"
      data-hud="holographic"
    >
      <HudHoloAtmosphere v-if="!isFoundationSurface" />
      <TopBar />
      <template v-if="!isFoundationSurface">
        <MobileVoiceCockpitStrip />
        <LeftSidebar />
        <CenterWorkbench />
        <RightDock />
      </template>
      <VaultSurface v-if="isVaultSurface" />
      <DataSurface v-if="isDataSurface" />
      <SkillsSurface v-if="isSkillsSurface" />
      <OperatorMobileShell v-if="isMobileSurface" />
      <OperatorSettingsSurface v-if="isSettingsSurface" />
      <StatusBar />
    </div>
    <VoiceOrbHost v-if="bootComplete && !isFoundationSurface" />
  </template>
</template>
