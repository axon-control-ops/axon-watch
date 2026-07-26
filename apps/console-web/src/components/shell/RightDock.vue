<script setup lang="ts">
import { computed, ref } from 'vue';

import AgentDock from '../ide/AgentDock.vue';
import ConversationSeamPanel from '../ConversationSeamPanel.vue';
import DockHeroPanel from '../DockHeroPanel.vue';
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

/** Mission Control mockup: LIVE OPERATIONS owns the right rail on Brain + Grid. */
const showLiveOpsDock = computed(
  () => shell.layoutMode === 'operator',
);
const brainStage = computed(() => shell.operatorBrainGalaxyActive);
</script>

<template>
  <AgentDock v-if="shell.layoutMode === 'ide'" />

  <aside
    v-else-if="showLiveOpsDock"
    ref="dockRef"
    class="region region-right-dock dock-stack dock-stack--mockup dock-stack--operator-conversation dock-stack--live-ops right-dock--resizable"
    :class="{
      'right-dock--resizing': resizing,
      'dock-stack--live-ops-brain': brainStage,
    }"
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

    <div class="dock-stack__upper dock-stack__upper--conversation dock-stack__upper--live-ops">
      <HudSeamCard
        seam-id="dock-seam-thread"
        title="Live operations"
        seam-class="dock-seam dock-seam--thread dock-seam--live-ops"
        :collapsed="false"
        compact-summary="VAXON orb · stream · reply"
        :collapsible="false"
      >
        <MissionControlLiveOpsPanel />
        <div
          v-if="!brainStage && shell.operatorThreadMessages.length"
          class="mission-control-receipts"
          aria-label="Operator conversation receipts"
        >
          <p class="mission-control-receipts__label">Operator receipts</p>
          <ConversationSeamPanel />
        </div>
      </HudSeamCard>
    </div>

    <!-- Brain stage matches mockup: orb card fills the rail (no briefing stack). -->
    <DockHeroPanel v-if="!brainStage" />
  </aside>
</template>

<style scoped>
.dock-stack--live-ops .dock-stack__upper--live-ops {
  flex: 1 1 auto;
  min-height: 0;
}

.dock-stack--live-ops-brain .dock-stack__upper--live-ops {
  flex: 1 1 auto;
  height: 100%;
}

.dock-stack--live-ops :deep(.dock-seam--live-ops.hud-seam) {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

.dock-stack--live-ops :deep(.dock-seam--live-ops .hud-seam__body) {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
}

.dock-stack--live-ops :deep(.dock-seam--live-ops .hud-seam__header) {
  display: none;
}

.mission-control-receipts {
  flex: 0 1 28%;
  min-height: 4rem;
  border-top: 1px solid rgba(0, 242, 255, 0.14);
  overflow: hidden;
}

.mission-control-receipts__label {
  margin: 0;
  padding: 0.35rem 0.55rem 0.2rem;
  color: rgba(148, 163, 184, 0.8);
  font: 0.5rem var(--font-mono);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
</style>
