<script setup lang="ts">
import { ref } from 'vue';

import AgentDock from '../ide/AgentDock.vue';
import ConversationSeamPanel from '../ConversationSeamPanel.vue';
import DockHeroPanel from '../DockHeroPanel.vue';
import HudSeamCard from '../HudSeamCard.vue';
import { useRightDockResize } from '../../composables/useRightDockResize';
import { useShellStore } from '../../stores/shell';
import MissionControlActivityPanel from './MissionControlActivityPanel.vue';

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
</script>

<template>
  <AgentDock v-if="shell.layoutMode === 'ide'" />

  <aside
    v-else-if="!shell.operatorBrainGalaxyActive"
    ref="dockRef"
    class="region region-right-dock dock-stack dock-stack--mockup dock-stack--operator-conversation right-dock--resizable"
    :class="{ 'right-dock--resizing': resizing }"
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

    <div class="dock-stack__upper dock-stack__upper--conversation">
      <HudSeamCard
        seam-id="dock-seam-thread"
        title="Live operations"
        seam-class="dock-seam dock-seam--thread"
        :collapsed="shell.dockSeamState('thread')?.collapsed ?? false"
        compact-summary="Autonomous workers, CI repairs, signals, and receipts"
        :collapsible="true"
        @toggle="shell.toggleDockSeam('thread')"
      >
        <MissionControlActivityPanel />
        <div
          v-if="shell.operatorThreadMessages.length"
          class="mission-control-receipts"
          aria-label="Operator conversation receipts"
        >
          <p class="mission-control-receipts__label">Operator receipts</p>
          <ConversationSeamPanel />
        </div>
      </HudSeamCard>
    </div>

    <DockHeroPanel />
  </aside>
</template>

<style scoped>
.mission-control-receipts {
  flex: 0 1 35%;
  min-height: 5rem;
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
