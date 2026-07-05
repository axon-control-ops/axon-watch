<script setup lang="ts">
import AgentDock from '../ide/AgentDock.vue';
import ConversationSeamPanel from '../ConversationSeamPanel.vue';
import DockHeroPanel from '../DockHeroPanel.vue';
import HudSeamCard from '../HudSeamCard.vue';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
</script>

<template>
  <AgentDock v-if="shell.layoutMode === 'ide'" />

  <aside
    v-else
    class="region region-right-dock dock-stack dock-stack--mockup dock-stack--operator-conversation"
  >
    <div class="dock-stack__upper dock-stack__upper--conversation">
      <HudSeamCard
        seam-id="dock-seam-thread"
        :title="shell.dockSeamState('thread')?.title ?? 'Conversation'"
        seam-class="dock-seam dock-seam--thread"
        :collapsed="false"
        :compact-summary="shell.dockSeamState('thread')?.compactSummary"
        :collapsible="false"
      >
        <ConversationSeamPanel />
      </HudSeamCard>
    </div>

    <DockHeroPanel />
  </aside>
</template>
