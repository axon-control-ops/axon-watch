<script setup lang="ts">
import { computed } from 'vue';

import KairoPresenceBar from './KairoPresenceBar.vue';
import OperatorPresenceSettingsPanel from './OperatorPresenceSettingsPanel.vue';
import { navigateToAppSurface, type AppSurface } from '../../lib/app-surface-route';
import { useAppSurface } from '../../composables/useAppSurface';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const { appSurface: activeSurface } = useAppSurface();

const isFoundationSurface = computed(
  () => activeSurface.value === 'vault' || activeSurface.value === 'data',
);
const topbarSubtitle = computed(() => {
  if (isFoundationSurface.value) {
    return 'OPERATOR CONSOLE';
  }
  return shell.layoutMode === 'ide' ? 'IDE WORKSPACE' : 'OPERATOR CONSOLE';
});
const showTopbarKairoPresence = computed(() => !isFoundationSurface.value);

function openSurface(surface: AppSurface): void {
  navigateToAppSurface(surface);
}
</script>

<template>
  <header class="region region-topbar topbar-mockup">
    <div class="topbar-mockup__grid">
      <div class="topbar-mockup__identity-zone">
        <div class="topbar-mockup__brand">
          <p class="topbar-mockup__subtitle">{{ topbarSubtitle }}</p>
        </div>
      </div>

      <div v-if="shell.topbarChips.length" class="topbar-mockup__runtime-strip chip-row">
        <span
          v-for="chip in shell.topbarChips"
          :key="chip.id"
          class="chip"
          :class="`chip--${chip.tone}`"
        >
          {{ chip.label }}
        </span>
      </div>

      <KairoPresenceBar
        v-if="showTopbarKairoPresence"
        :state="shell.kairoPresenceState"
        @open-briefing="shell.focusKairoBriefing()"
      />

      <div class="topbar-mockup__controls">
        <div
          class="layout-toggle layout-toggle--mockup topbar-mockup__surface-nav"
          role="group"
          aria-label="Operator surfaces"
        >
          <button
            v-if="activeSurface !== 'console'"
            type="button"
            class="layout-toggle__button layout-toggle__button--active"
            aria-current="page"
            @click="openSurface('console')"
          >
            ← CONSOLE
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
            aria-label="Settings"
            aria-haspopup="dialog"
            :aria-expanded="shell.operatorPresenceSettingsOpen"
            @click="shell.toggleOperatorPresenceSettingsPanel()"
          >
            ⚙
          </button>
          <OperatorPresenceSettingsPanel
            :open="shell.operatorPresenceSettingsOpen"
            :settings="shell.operatorPresenceSettings"
            :saving="shell.operatorPresenceSettingsSaving"
            @close="shell.toggleOperatorPresenceSettingsPanel(false)"
            @save="shell.saveOperatorPresenceSettingsPatch($event)"
          />
        </div>
      </div>
    </div>
  </header>
</template>

<style scoped>
.topbar-mockup__settings-wrap {
  position: relative;
}

.topbar-mockup__surface-nav {
  margin-right: 0.35rem;
}
</style>
