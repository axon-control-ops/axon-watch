<script setup lang="ts">
import { ref } from 'vue';

import AgentDock from '../ide/AgentDock.vue';
import ConversationSeamPanel from '../ConversationSeamPanel.vue';
import DockHeroPanel from '../DockHeroPanel.vue';
import HudSeamCard from '../HudSeamCard.vue';
import { useRightDockResize } from '../../composables/useRightDockResize';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const dockRef = ref<HTMLElement | null>(null);

const { resizing, resetDockWidth, startDockResize } = useRightDockResize({ dockRef });
</script>

<template>
  <AgentDock v-if="shell.layoutMode === 'ide'" />

  <aside
    v-else
    ref="dockRef"
    class="region region-right-dock dock-stack dock-stack--mockup dock-stack--operator-conversation right-dock--resizable"
    :class="{ 'right-dock--resizing': resizing }"
  >
    <div
      class="right-dock__resize-handle"
      title="Drag to resize the right dock. Double-click to reset."
      aria-hidden="true"
      @mousedown="startDockResize"
      @dblclick="resetDockWidth"
    >
      <span class="right-dock__resize-grip" />
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

    <DockHeroPanel />
  </aside>
</template>
