<script setup lang="ts">
import { computed, ref } from 'vue';

import AgentDock from '../ide/AgentDock.vue';
import OperatorLiveOpsGlance from './OperatorLiveOpsGlance.vue';
import { useRightDockResize } from '../../composables/useRightDockResize';
import { defaultOperatorLiveOpsGlanceWidth, LIVE_OPS_WIDTH_KEY } from '../../lib/agent-dock-width';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const dockRef = ref<HTMLElement | null>(null);

const showOperatorGlance = computed(
  () => shell.layoutMode === 'operator' && !shell.operatorBrainGalaxyActive,
);

const {
  dockWidth,
  resizing,
  ariaValueMin,
  ariaValueMax,
  resetDockWidth,
  startDockResize,
  onDockResizeKeydown,
} = useRightDockResize({
  dockRef,
  resolveDefaultWidth: defaultOperatorLiveOpsGlanceWidth,
  storageKey: LIVE_OPS_WIDTH_KEY,
  cssVarName: '--shell-live-ops-width',
});
</script>

<template>
  <AgentDock v-if="shell.layoutMode === 'ide'" />

  <aside
    v-else-if="showOperatorGlance"
    ref="dockRef"
    class="region region-right-dock dock-stack dock-stack--mockup dock-stack--live-ops-glance right-dock--resizable"
    :class="{ 'right-dock--resizing': resizing }"
    aria-label="Live operations glance"
  >
    <div
      class="right-dock__resize-handle"
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize live ops panel"
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

    <OperatorLiveOpsGlance />
  </aside>
</template>
