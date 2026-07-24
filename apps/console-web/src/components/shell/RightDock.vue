<script setup lang="ts">
import { ref } from 'vue';

import AgentDock from '../ide/AgentDock.vue';
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
      </HudSeamCard>
    </div>

    <DockHeroPanel />
  </aside>
</template>
