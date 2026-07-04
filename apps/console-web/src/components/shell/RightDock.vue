<script setup lang="ts">
import ConversationSeamPanel from '../ConversationSeamPanel.vue';
import AttentionStackPanel from './AttentionStackPanel.vue';
import DockHeroPanel from '../DockHeroPanel.vue';
import HudSeamCard from '../HudSeamCard.vue';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
</script>

<template>
  <aside
    class="region region-right-dock dock-stack dock-stack--mockup"
    :class="{ 'dock-stack--operator-conversation': shell.layoutMode === 'operator' }"
  >
    <div
      class="dock-stack__upper"
      :class="{ 'dock-stack__upper--conversation': shell.layoutMode === 'operator' }"
    >
      <AttentionStackPanel v-if="shell.layoutMode === 'ide'" variant="dock" />

      <HudSeamCard
        seam-id="dock-seam-thread"
        :title="shell.dockSeamState('thread')?.title ?? 'Conversation'"
        seam-class="dock-seam dock-seam--thread"
        :collapsed="shell.layoutMode === 'operator' ? false : (shell.dockSeamState('thread')?.collapsed ?? false)"
        :compact-summary="shell.dockSeamState('thread')?.compactSummary"
        :collapsible="shell.layoutMode === 'ide'"
        @toggle="shell.toggleDockSeam('thread')"
      >
        <ConversationSeamPanel />
      </HudSeamCard>
    </div>

    <DockHeroPanel />
  </aside>
</template>
