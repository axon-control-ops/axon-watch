<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';

import { OPERATOR_AUTH_REQUIRED_EVENT } from './api/client';
import { fetchOperatorSession, type OperatorSessionStatus } from './api/operator-auth-api';
import BootWakeOverlay from './components/BootWakeOverlay.vue';
import OperatorLoginGate from './components/auth/OperatorLoginGate.vue';
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
import ReportTheaterOverlay from './features/report-theater/ReportTheaterOverlay.vue';
import './features/report-theater/report-theater.css';
import HudHoloAtmosphere from './features/hud-holo/HudHoloAtmosphere.vue';
import { useShellStore } from './stores/shell';

const shell = useShellStore();
useIdeLayoutShortcuts();
useIdeKairoInterrupt();
useVoiceDeckOnBoot();
useVoiceCockpitPresence();
useKairoAppVoice();
let liveEventsSession: ReturnType<typeof startLiveEventsSession> | null = null;
const operatorAuthState = ref<'checking' | 'authenticated' | 'required' | 'error'>('checking');
const operatorAuthError = ref<string | null>(null);
const operatorSessionHint = ref<OperatorSessionStatus | null>(null);
let bootstrapStarted = false;
const { appSurface } = useAppSurface();
const isVaultSurface = computed(() => appSurface.value === 'vault');
const isDataSurface = computed(() => appSurface.value === 'data');
const isSkillsSurface = computed(() => appSurface.value === 'skills');
const isMobileSurface = computed(() => appSurface.value === 'mobile');
const isSettingsSurface = computed(() => appSurface.value === 'settings');
const mobileSurfaceGridStyle = {
  gridTemplateAreas: "'mobile'",
  gridTemplateColumns: 'minmax(0, 1fr)',
  gridTemplateRows: 'minmax(0, 1fr)',
  minWidth: '0',
  width: '100%',
  height: '100vh',
};
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

function markOperatorAuthenticated(): void {
  operatorAuthState.value = 'authenticated';
  operatorAuthError.value = null;
  if (!bootstrapStarted) {
    bootstrapStarted = true;
    void shell.loadBootstrapData();
  }
}

async function checkOperatorSession(): Promise<void> {
  operatorAuthState.value = 'checking';
  operatorAuthError.value = null;
  try {
    const status = await fetchOperatorSession();
    operatorSessionHint.value = status;
    if (status.authenticated) {
      markOperatorAuthenticated();
      return;
    }
    operatorAuthState.value = 'required';
  } catch (error) {
    operatorAuthState.value = 'error';
    operatorAuthError.value =
      error instanceof Error ? error.message : 'Operator session check failed.';
  }
}

function requireOperatorAuthentication(): void {
  operatorAuthState.value = 'required';
  liveEventsSession?.disconnect();
  liveEventsSession = null;
}

onMounted(() => {
  window.addEventListener(OPERATOR_AUTH_REQUIRED_EVENT, requireOperatorAuthentication);
  void checkOperatorSession();
});

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
  () => [bootComplete.value, operatorAuthState.value] as const,
  ([complete, authState]) => {
    if (!complete || authState !== 'authenticated' || showScanPreview.value) {
      shell.unbindViewportCompactListener();
      liveEventsSession?.disconnect();
      liveEventsSession = null;
      return;
    }

    shell.bindViewportCompactListener();

    liveEventsSession?.disconnect();
    liveEventsSession = startLiveEventsSession({
      onRefresh: () => {
        // IDE must stay interactive: skip heavy operator surface refresh while
        // coding/streaming. Operator layout still needs light run refresh.
        if (shell.layoutMode === 'ide') {
          // Runtime summary (watch connectivity, CLI status) must still
          // self-heal here, or a transient watch outage leaves the WATCH
          // OFFLINE banner stuck indefinitely — this is the only surface
          // refresh call left running while the operator stays in IDE mode.
          // background:true is cheap (dedup'd in-flight, no loading-state
          // flip) and touches nothing else, so it's safe during streaming.
          return shell.loadRuntimeSummary({ background: true });
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
      onSpokenLine: (event) => shell.speakSpokenLine(event),
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
  window.removeEventListener(OPERATOR_AUTH_REQUIRED_EVENT, requireOperatorAuthentication);
  shell.unbindViewportCompactListener();
  liveEventsSession?.disconnect();
  liveEventsSession = null;
});
</script>

<template>
  <OperatorLoginGate
    v-if="operatorAuthState !== 'authenticated'"
    :checking="operatorAuthState === 'checking'"
    :connection-error="operatorAuthError"
    :loopback-bypass="operatorSessionHint?.loopback_bypass === true"
    :cookie-max-age-seconds="operatorSessionHint?.cookie_max_age_seconds ?? null"
    @authenticated="markOperatorAuthenticated"
    @retry="checkOperatorSession"
  />

  <template v-else>
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
          'console-shell--mission-control':
            shell.layoutMode === 'operator' && !shell.operatorBrainGalaxyActive,
          'console-shell--glass3d': !isFoundationSurface,
          'console-shell--vault': isVaultSurface,
          'console-shell--data': isDataSurface,
          'console-shell--skills': isSkillsSurface,
          'console-shell--mobile': isMobileSurface,
          'console-shell--settings': isSettingsSurface,
        }"
        :style="isMobileSurface ? mobileSurfaceGridStyle : undefined"
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
      <ReportTheaterOverlay v-if="bootComplete && !isFoundationSurface" />
    </template>
  </template>
</template>
