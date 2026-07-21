<script setup lang="ts">
import { computed, watch } from 'vue';

import IdeInterruptPanel from '../ide/IdeInterruptPanel.vue';
import KairoPresenceBar from './KairoPresenceBar.vue';
import AxonProductLogo from '../../components/AxonProductLogo.vue';
import { navigateToAppSurface, type AppSurface } from '../../lib/app-surface-route';
import { useAppSurface } from '../../composables/useAppSurface';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const { appSurface: activeSurface } = useAppSurface();

const isFoundationSurface = computed(
  () =>
    activeSurface.value === 'vault' ||
    activeSurface.value === 'data' ||
    activeSurface.value === 'skills' ||
    activeSurface.value === 'settings',
);
const topbarSubtitle = computed(() => {
  if (activeSurface.value === 'settings') {
    return 'SETTINGS';
  }
  if (activeSurface.value === 'skills') {
    return 'SKILLS';
  }
  if (isFoundationSurface.value) {
    return 'OPERATOR CONSOLE';
  }
  return shell.layoutMode === 'ide' ? 'IDE WORKSPACE' : 'OPERATOR CONSOLE';
});
const showTopbarKairoPresence = computed(
  () => activeSurface.value === 'console',
);
const showIdeInterruptTopbar = computed(
  () =>
    activeSurface.value === 'console' &&
    shell.layoutMode === 'ide' &&
    shell.idePresenceProfile === 'interrupt',
);

watch(
  () => ({
    displayedState: shell.ideDisplayKairoPresenceState,
    baseState: shell.kairoPresenceState,
    profile: shell.idePresenceProfile,
    speechActive: shell.kairoSpeechActive,
    voicePaused: shell.kairoVoicePaused,
    agentStreamActive: shell.agentStreamActive,
    activeEmployeeRole: shell.activeIdeEmployee?.role ?? null,
    hasEmployeeFailure: Boolean(shell.activeIdeEmployeeFailureLine),
    criticalSignals: shell.runtimeSummary?.signals.critical_count ?? null,
    highSignals: shell.runtimeSummary?.signals.high_count ?? null,
    watchConnected: shell.runtimeSummary?.watch.connected ?? null,
  }),
  (next, previous) => {
    // #region agent log
    fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'fc0b35'},body:JSON.stringify({sessionId:'fc0b35',runId:'topbar-state',hypothesisId:'H2,H3,H4',location:'TopBar.vue:presence-watch',message:'topbar presence inputs changed',data:{previous,next},timestamp:Date.now()})}).catch(()=>{});
    // #endregion
  },
  { immediate: true },
);

function openSurface(surface: AppSurface): void {
  navigateToAppSurface(surface);
}

function openSettings(): void {
  navigateToAppSurface('settings');
}
</script>

<template>
  <header class="region region-topbar topbar-mockup">
    <div
      class="topbar-mockup__grid"
      :class="{ 'topbar-mockup__grid--ide-interrupt': showIdeInterruptTopbar }"
    >
      <div class="topbar-mockup__identity-zone">
        <div class="topbar-mockup__brand">
          <AxonProductLogo />
          <p class="topbar-mockup__subtitle">{{ topbarSubtitle }}</p>
        </div>
      </div>

      <IdeInterruptPanel v-if="showIdeInterruptTopbar" class="topbar-mockup__runtime-strip" />
      <div
        v-else-if="shell.topbarChips.length"
        class="topbar-mockup__runtime-strip chip-row"
      >
        <span
          v-for="chip in shell.topbarChips"
          :key="chip.id"
          class="chip"
          :class="`chip--${chip.tone}`"
        >
          {{ chip.label }}
        </span>
      </div>

      <div class="topbar-mockup__kairo-slot">
        <KairoPresenceBar
          v-if="showTopbarKairoPresence"
          compact
          :state="
            shell.layoutMode === 'ide'
              ? shell.ideDisplayKairoPresenceState
              : shell.kairoPresenceState
          "
          :speech-active="shell.kairoSpeechActive && !shell.kairoVoicePaused"
          :paused="shell.kairoVoicePaused"
          @action="shell.handleKairoPresenceAction()"
        />
      </div>

      <div class="topbar-mockup__controls">
        <div
          class="layout-toggle layout-toggle--mockup topbar-mockup__surface-nav"
          role="group"
          aria-label="Operator surfaces"
        >
          <button
            v-if="activeSurface !== 'console'"
            type="button"
            class="layout-toggle__button"
            @click="openSurface('console')"
          >
            CONSOLE
          </button>
          <button
            v-if="activeSurface !== 'vault'"
            type="button"
            class="layout-toggle__button"
            @click="openSurface('vault')"
          >
            VAULT
          </button>
          <button
            v-if="activeSurface !== 'data'"
            type="button"
            class="layout-toggle__button"
            @click="openSurface('data')"
          >
            DATA
          </button>
          <button
            v-if="activeSurface !== 'skills'"
            type="button"
            class="layout-toggle__button"
            @click="openSurface('skills')"
          >
            SKILLS
          </button>
        </div>
        <div
          v-if="!isFoundationSurface"
          class="layout-toggle layout-toggle--mockup"
          role="group"
          aria-label="Layout mode"
        >
          <button
            type="button"
            class="layout-toggle__button"
            :class="{ 'layout-toggle__button--active': shell.layoutMode === 'operator' }"
            :aria-pressed="shell.layoutMode === 'operator'"
            @click="shell.setLayoutMode('operator')"
          >
            OPERATOR
          </button>
          <button
            type="button"
            class="layout-toggle__button"
            :class="{ 'layout-toggle__button--active': shell.layoutMode === 'ide' }"
            :aria-pressed="shell.layoutMode === 'ide'"
            @click="shell.setLayoutMode('ide')"
          >
            IDE
          </button>
        </div>
        <div class="topbar-mockup__settings-wrap">
          <button
            type="button"
            class="topbar-mockup__settings"
            :class="{ 'topbar-mockup__settings--active': activeSurface === 'settings' }"
            aria-label="Settings"
            :aria-current="activeSurface === 'settings' ? 'page' : undefined"
            @click.stop="openSettings()"
          >
            ⚙
          </button>
        </div>
      </div>
    </div>
  </header>
</template>

<style scoped>
.topbar-mockup__kairo-slot {
  min-width: 0;
  overflow: hidden;
}

.topbar-mockup__settings-wrap {
  position: relative;
  z-index: 12;
}

.topbar-mockup__settings--active {
  border-color: rgba(0, 242, 255, 0.55);
  box-shadow: 0 0 0 1px rgba(0, 242, 255, 0.22);
}

.topbar-mockup__surface-nav {
  margin-right: 0.35rem;
}

:deep(.topbar-mockup__runtime-strip.ide-interrupt-topbar) {
  flex: 1 1 auto;
}
</style>
