<script setup lang="ts">
import { computed, ref } from 'vue';

import AgentDock from '../ide/AgentDock.vue';
import HudSeamCard from '../HudSeamCard.vue';
import { useRightDockResize } from '../../composables/useRightDockResize';
import { useShellStore } from '../../stores/shell';
import MissionControlLiveOpsPanel from './MissionControlLiveOpsPanel.vue';

const shell = useShellStore();
const dockRef = ref<HTMLElement | null>(null);

const {
  dockWidth,
  resizing,
  ariaValueMin,
  ariaValueMax,
  resetDockWidth,
  startDockResize,
  onDockResizeKeydown,
} = useRightDockResize({ dockRef });

/** Mission Control owns LIVE OPERATIONS; Brain Graph uses a floating orb instead. */
const showLiveOpsDock = computed(
  () => shell.layoutMode === 'operator' && !shell.operatorBrainGalaxyActive,
);
</script>

<template>
  <AgentDock v-if="shell.layoutMode === 'ide'" />

  <aside
    v-else-if="showLiveOpsDock"
    ref="dockRef"
    class="region region-right-dock dock-stack dock-stack--mockup dock-stack--live-ops dock-stack--live-ops-only right-dock--resizable"
    :class="{ 'right-dock--resizing': resizing }"
    aria-label="LIVE OPERATIONS"
  >
    <div
      class="right-dock__resize-handle"
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize right dock"
      title="Drag or use arrow keys to resize. Enter or double-click to reset."
      tabindex="0"
      :aria-valuemin="ariaValueMin"
      :aria-valuemax="ariaValueMax"
      :aria-valuenow="dockWidth"
      @mousedown="startDockResize"
      @keydown="onDockResizeKeydown"
      @dblclick="resetDockWidth"
    >
      <span class="right-dock__resize-grip" aria-hidden="true" />
    </div>

    <div class="dock-stack__live-ops-frame">
      <!--
        Collapsible thread seam kept for dock-behavior contract; chrome is
        visually suppressed so LIVE OPERATIONS fills the mockup card.
      -->
      <HudSeamCard
        seam-id="dock-seam-thread"
        title="Live operations"
        seam-class="dock-seam dock-seam--thread dock-seam--live-ops"
        :collapsed="shell.dockSeamState('thread')?.collapsed ?? false"
        compact-summary="VAXON orb · stream · reply"
        :collapsible="true"
        @toggle="shell.toggleDockSeam('thread')"
      >
        <MissionControlLiveOpsPanel />
      </HudSeamCard>
    </div>
  </aside>
</template>

<style scoped>
.dock-stack--live-ops-only {
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 0.45rem;
  background:
    linear-gradient(180deg, rgba(0, 28, 42, 0.55), rgba(0, 10, 18, 0.72)),
    rgba(2, 8, 14, 0.92);
}

.dock-stack__live-ops-frame {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(70, 210, 255, 0.42);
  border-radius: 0.55rem;
  box-shadow:
    inset 0 0 0 1px rgba(0, 200, 255, 0.08),
    0 0 1.4rem rgba(0, 160, 220, 0.12);
  background:
    radial-gradient(ellipse at 50% 12%, rgba(0, 120, 180, 0.18), transparent 55%),
    rgba(1, 8, 14, 0.94);
  overflow: hidden;
}

.dock-stack--live-ops-only :deep(.dock-seam--live-ops.hud-seam) {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
}

.dock-stack--live-ops-only :deep(.dock-seam--live-ops .hud-seam__header),
.dock-stack--live-ops-only :deep(.dock-seam--live-ops .hud-seam__corner),
.dock-stack--live-ops-only :deep(.dock-seam--live-ops .hud-seam__compact) {
  display: none;
}

.dock-stack--live-ops-only :deep(.dock-seam--live-ops .hud-seam__body) {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  padding: 0;
}

.dock-stack--live-ops-only :deep(.mc-live-ops) {
  min-height: 0;
  max-height: 100%;
}
</style>
