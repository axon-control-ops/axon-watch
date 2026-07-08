<script setup lang="ts">
import BriefingPanel from './BriefingPanel.vue';
import CommandSeamPanel from './CommandSeamPanel.vue';
import BriefingSeamIcon from './BriefingSeamIcon.vue';
import PersonaTitle from './PersonaTitle.vue';
import { useShellStore } from '../stores/shell';

const shell = useShellStore();
</script>

<template>
  <section
    id="dock-seam-briefing"
    class="hud-seam dock-seam dock-seam--briefing dock-hero-panel"
    :class="{
      'hud-seam--hero': true,
      'hud-seam--emphasized': shell.briefingSeamEmphasized,
      'dock-hero-panel--command': shell.dockHeroMode === 'command',
      'dock-hero-panel--briefing': shell.dockHeroMode === 'briefing',
    }"
  >
    <span class="hud-seam__corner hud-seam__corner--tl" aria-hidden="true" />
    <span class="hud-seam__corner hud-seam__corner--tr" aria-hidden="true" />
    <span class="hud-seam__corner hud-seam__corner--bl" aria-hidden="true" />
    <span class="hud-seam__corner hud-seam__corner--br" aria-hidden="true" />

    <div class="hud-seam__header dock-hero-panel__header">
      <div class="hud-seam__title-block">
        <BriefingSeamIcon v-if="shell.dockHeroMode === 'briefing'" />
        <p v-if="shell.dockHeroMode === 'briefing'" class="hud-seam__title">
          <PersonaTitle suffix="Briefing" mark-size="xs" />
        </p>
        <p v-else class="hud-seam__title">Command</p>
      </div>
      <div class="dock-hero-panel__toggle" role="tablist" aria-label="Dock hero mode">
        <button
          type="button"
          role="tab"
          class="dock-hero-panel__toggle-button"
          :class="{ 'dock-hero-panel__toggle-button--active': shell.dockHeroMode === 'command' }"
          :aria-selected="shell.dockHeroMode === 'command'"
          @click="shell.setDockHeroMode('command')"
        >
          Command
        </button>
        <button
          type="button"
          role="tab"
          class="dock-hero-panel__toggle-button dock-hero-panel__toggle-button--kairo"
          :class="{
            'dock-hero-panel__toggle-button--active': shell.dockHeroMode === 'briefing',
            'dock-hero-panel__toggle-button--attention': shell.showKairoBriefingAttention,
            [`dock-hero-panel__toggle-button--attention-${shell.kairoBriefingAttention.severity}`]:
              shell.showKairoBriefingAttention,
          }"
          :aria-selected="shell.dockHeroMode === 'briefing'"
          @click="shell.setDockHeroMode('briefing')"
        >
          <PersonaTitle mark-size="xs" />
          <span
            v-if="shell.showKairoBriefingAttention"
            class="dock-hero-panel__toggle-badge"
            aria-hidden="true"
          >
            {{ shell.kairoBriefingAttention.badgeCount }}
          </span>
        </button>
      </div>
    </div>

    <div class="hud-seam__body dock-hero-panel__body">
      <CommandSeamPanel
        v-show="shell.dockHeroMode === 'command'"
        class="dock-hero-panel__surface"
        compact
      />
      <BriefingPanel
        v-show="shell.dockHeroMode === 'briefing'"
        class="dock-hero-panel__surface"
        :briefing="shell.operatorBriefing"
        :load-state="shell.briefingLoadState"
        :error="shell.briefingError"
        :summary-line="shell.briefingSummaryLine"
        :hero="true"
        :galaxy-compact="shell.operatorBrainGalaxyActive"
        @open-chat="shell.setDockHeroMode('command')"
      />
    </div>
  </section>
</template>
