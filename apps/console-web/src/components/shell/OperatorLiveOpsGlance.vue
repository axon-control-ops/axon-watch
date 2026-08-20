<script setup lang="ts">
import { computed } from 'vue';

import { useMcVaxonPresence } from '../../composables/use-mc-vaxon-presence';
import { useShellStore } from '../../stores/shell';
import McVaxonHeroBlock from './McVaxonHeroBlock.vue';
import MissionControlMachineCeoStrip from './MissionControlMachineCeoStrip.vue';

const shell = useShellStore();
const isVaxonTab = computed(() => shell.operatorCenterView === 'vaxon');

const { autonomyMode, fullAutonomyActive, liveBadge, modeChip, streamItems } =
  useMcVaxonPresence();
</script>

<template>
  <aside
    class="operator-live-ops-glance hud-panel-frame"
    :class="{ 'operator-live-ops-glance--vaxon': isVaxonTab }"
    aria-label="Live operations glance"
  >
    <span class="hud-panel-frame__corner hud-panel-frame__corner--tl" aria-hidden="true" />
    <span class="hud-panel-frame__corner hud-panel-frame__corner--tr" aria-hidden="true" />
    <span class="hud-panel-frame__corner hud-panel-frame__corner--bl" aria-hidden="true" />
    <span class="hud-panel-frame__corner hud-panel-frame__corner--br" aria-hidden="true" />

    <header class="operator-live-ops-glance__head">
      <p class="operator-live-ops-glance__eyebrow">Live ops</p>
      <span class="operator-live-ops-glance__live" :data-live="liveBadge ? 'true' : 'false'">
        {{ liveBadge ? '● Live' : 'Standby' }}
      </span>
    </header>

    <MissionControlMachineCeoStrip />

    <section
      v-if="isVaxonTab"
      class="operator-live-ops-glance__vaxon-card"
      aria-label="VAXON presence"
    >
      <header class="operator-live-ops-glance__section-head">
        <p class="operator-live-ops-glance__section-label">VAXON</p>
        <span class="operator-live-ops-glance__section-mode">{{ modeChip }}</span>
      </header>

      <McVaxonHeroBlock
        dock-rail
        :mode-chip="modeChip"
        :full-autonomy-active="fullAutonomyActive"
        :autonomy-mode="autonomyMode"
      />
    </section>

    <section
      v-if="isVaxonTab"
      class="operator-live-ops-glance__feed"
      aria-label="Live operations feed"
    >
      <header class="operator-live-ops-glance__section-head">
        <p class="operator-live-ops-glance__section-label">Live feed</p>
        <span class="operator-live-ops-glance__section-count">{{ streamItems.length }}</span>
      </header>

      <ul
        v-if="streamItems.length"
        class="operator-live-ops-glance__stream"
        aria-label="Live updates"
      >
        <li
          v-for="item in streamItems"
          :key="item.id"
          class="operator-live-ops-glance__stream-item"
          :data-tone="item.tone"
        >
          <span class="operator-live-ops-glance__stream-at">{{ item.at }}</span>
          <span class="operator-live-ops-glance__stream-agent">{{ item.agent }}</span>
          <span class="operator-live-ops-glance__stream-text">{{ item.text }}</span>
        </li>
      </ul>
      <p v-else class="operator-live-ops-glance__feed-empty">
        Fleet activity will appear here as agents work.
      </p>
    </section>
  </aside>
</template>

<style scoped>
.operator-live-ops-glance {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  min-height: 0;
  height: 100%;
  padding: 0.65rem 0.7rem 0.75rem;
  border: 1px solid rgba(70, 210, 255, 0.28);
  border-radius: 0.55rem;
  background:
    linear-gradient(180deg, rgba(0, 28, 42, 0.55), rgba(0, 10, 18, 0.72)),
    rgba(2, 8, 14, 0.92);
  box-shadow: inset 0 0 0 1px rgba(0, 200, 255, 0.08);
  overflow: hidden;
}

.operator-live-ops-glance--vaxon {
  gap: 0.4rem;
}

.operator-live-ops-glance__vaxon-card {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  flex: 1 1 auto;
  min-height: 18rem;
  padding: 0.42rem 0.45rem 0.48rem;
  border: 1px solid rgba(72, 220, 255, 0.24);
  border-radius: 0.48rem;
  background:
    radial-gradient(ellipse 90% 55% at 50% 0%, rgba(0, 180, 230, 0.1), transparent 58%),
    rgba(2, 14, 24, 0.82);
  overflow: hidden;
}

.operator-live-ops-glance__section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.4rem;
  flex-shrink: 0;
}

.operator-live-ops-glance__section-label {
  margin: 0;
  color: rgba(140, 235, 255, 0.88);
  font: 0.52rem var(--font-mono, ui-monospace, monospace);
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.operator-live-ops-glance__section-mode,
.operator-live-ops-glance__section-count {
  padding: 0.08rem 0.35rem;
  border-radius: 999px;
  border: 1px solid rgba(72, 200, 255, 0.22);
  color: rgba(168, 228, 248, 0.88);
  font: 0.46rem var(--font-mono, ui-monospace, monospace);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.operator-live-ops-glance__vaxon-card :deep(.mc-vaxon-hero) {
  flex: 1 1 auto;
  min-height: 0;
}

.operator-live-ops-glance__vaxon-card :deep(.mc-vaxon-hero__orb) {
  border-color: rgba(96, 240, 255, 0.38);
  background:
    radial-gradient(circle at 50% 38%, rgba(0, 220, 255, 0.22), transparent 52%),
    radial-gradient(circle at 50% 82%, rgba(0, 70, 120, 0.42), transparent 58%),
    rgba(1, 8, 16, 0.96);
}

.operator-live-ops-glance__vaxon-card :deep(.mc-vaxon-hero__orb-visual) {
  min-height: 16rem;
}

.operator-live-ops-glance__vaxon-card :deep(.kairo-galaxy-orb__trigger) {
  width: min(100%, 16.5rem);
  height: min(100%, 16.5rem);
}

.operator-live-ops-glance__vaxon-card :deep(.kairo-galaxy-orb__cinematic-art) {
  opacity: 1;
}

.operator-live-ops-glance__feed {
  display: flex;
  flex-direction: column;
  gap: 0.32rem;
  flex: 0 1 auto;
  max-height: 9.5rem;
  min-height: 4.5rem;
}

.operator-live-ops-glance__feed-empty {
  margin: 0;
  padding: 0.35rem 0.42rem;
  border: 1px dashed rgba(70, 200, 255, 0.18);
  border-radius: 0.38rem;
  color: rgba(120, 170, 195, 0.72);
  font: 0.52rem / 1.4 var(--font-mono, ui-monospace, monospace);
}

.operator-live-ops-glance__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  flex-shrink: 0;
}

.operator-live-ops-glance__eyebrow {
  margin: 0;
  color: rgba(140, 235, 255, 0.92);
  font: 0.62rem var(--font-mono, ui-monospace, monospace);
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.operator-live-ops-glance__live {
  padding: 0.12rem 0.42rem;
  border: 1px solid rgba(70, 200, 255, 0.28);
  border-radius: 999px;
  color: rgba(148, 163, 184, 0.85);
  font: 0.48rem var(--font-mono, ui-monospace, monospace);
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.operator-live-ops-glance__live[data-live='true'] {
  border-color: rgba(255, 110, 120, 0.65);
  color: rgba(255, 130, 145, 0.96);
  background: rgba(70, 8, 18, 0.55);
}

.operator-live-ops-glance :deep(.mc-machine-ceo) {
  margin: 0;
  flex-shrink: 0;
}

.operator-live-ops-glance__stream {
  list-style: none;
  display: grid;
  align-content: start;
  gap: 0.28rem;
  flex: 1 1 auto;
  min-height: 0;
  margin: 0;
  padding: 0.35rem 0.42rem;
  overflow: auto;
  overscroll-behavior: contain;
  border: 1px solid rgba(70, 200, 255, 0.16);
  border-radius: 0.42rem;
  background: rgba(1, 10, 18, 0.72);
}

.operator-live-ops-glance__stream-item {
  display: grid;
  grid-template-columns: 3.6rem 3rem minmax(0, 1fr);
  gap: 0.32rem;
  margin: 0;
  color: rgba(210, 235, 248, 0.92);
  font-size: 0.52rem;
  line-height: 1.35;
}

.operator-live-ops-glance__stream-at {
  color: rgba(120, 170, 195, 0.85);
  font-family: var(--font-mono, ui-monospace, monospace);
}

.operator-live-ops-glance__stream-agent {
  color: rgba(100, 235, 255, 0.95);
  font: 0.48rem var(--font-mono, ui-monospace, monospace);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.operator-live-ops-glance__stream-item[data-tone='critical'] .operator-live-ops-glance__stream-text {
  color: rgba(255, 150, 170, 0.96);
}

.operator-live-ops-glance__stream-item[data-tone='attention'] .operator-live-ops-glance__stream-text {
  color: rgba(255, 210, 140, 0.95);
}
</style>
