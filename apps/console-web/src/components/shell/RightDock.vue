<script setup lang="ts">
import { ref } from 'vue';

import AgentDock from '../ide/AgentDock.vue';
import ConversationSeamPanel from '../ConversationSeamPanel.vue';
import DockHeroPanel from '../DockHeroPanel.vue';
import HudSeamCard from '../HudSeamCard.vue';
import { useRightDockResize } from '../../composables/useRightDockResize';
import { useVerticalPanelResize } from '../../composables/useVerticalPanelResize';
import { useShellStore } from '../../stores/shell';

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

const {
  panelSize: briefingHeight,
  resizing: briefingResizing,
  ariaValueMin: briefingHeightMin,
  ariaValueMax: briefingHeightMax,
  resetSize: resetBriefingHeight,
  startResize: startBriefingResize,
  onResizeKeydown: onBriefingResizeKeydown,
} = useVerticalPanelResize({
  rootRef: dockRef,
  cssVariable: '--briefing-dock-height',
  storageKey: 'axon-shell-briefing-card-height',
  defaultSize: (height) => Math.min(264, Math.max(190, height * 0.3)),
  minSize: 168,
  maxSize: (height) => height * 0.62,
});
</script>

<template>
  <AgentDock v-if="shell.layoutMode === 'ide'" />

  <aside
    v-else-if="!shell.operatorBrainGalaxyActive"
    ref="dockRef"
    class="region region-right-dock dock-stack dock-stack--mockup dock-stack--operator-conversation right-dock--resizable"
    :class="{
      'right-dock--resizing': resizing,
      'right-dock--briefing-resizing': briefingResizing,
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

    <div class="dock-stack__upper dock-stack__upper--conversation">
      <HudSeamCard
        seam-id="dock-seam-thread"
        :title="shell.layoutMode === 'operator' ? 'Operator thread' : 'Conversation'"
        seam-class="dock-seam dock-seam--thread"
        :collapsed="shell.dockSeamState('thread')?.collapsed ?? false"
        :compact-summary="
          shell.layoutMode === 'operator'
            ? 'Actions, KAIRO turns, and receipts — not the run queue'
            : shell.dockSeamState('thread')?.compactSummary
        "
        :collapsible="true"
        @toggle="shell.toggleDockSeam('thread')"
      >
        <ConversationSeamPanel />
      </HudSeamCard>
    </div>

    <div
      class="briefing-card-resize-handle"
      role="separator"
      aria-orientation="horizontal"
      aria-label="Resize Agent Briefing card"
      title="Drag or use arrow keys to resize. Enter or double-click to reset."
      tabindex="0"
      :aria-valuemin="briefingHeightMin"
      :aria-valuemax="briefingHeightMax"
      :aria-valuenow="briefingHeight"
      @mousedown="startBriefingResize"
      @keydown="onBriefingResizeKeydown"
      @dblclick="resetBriefingHeight"
    >
      <span class="briefing-card-resize-grip" aria-hidden="true" />
    </div>

    <DockHeroPanel />
  </aside>
</template>
