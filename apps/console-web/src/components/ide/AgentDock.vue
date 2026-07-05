<script setup lang="ts">
import { computed, ref } from 'vue';

import ConversationSeamPanel from '../ConversationSeamPanel.vue';
import { runPhaseTag } from '../../lib/mockup-shell-view';
import { useRightDockResize } from '../../composables/useRightDockResize';
import AgentDockComposer from './AgentDockComposer.vue';
import AgentDockWorkspaceMenu from './AgentDockWorkspaceMenu.vue';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const dockRef = ref<HTMLElement | null>(null);

const { resizing, resetDockWidth, startDockResize } = useRightDockResize({
  dockRef,
  collapsed: computed(() => shell.agentDockCollapsed),
});

const signalCount = computed(
  () => shell.operatorBriefing?.top_signals.length ?? shell.runtimeSummary?.signals.open_count ?? 0,
);

function collapseDock(): void {
  shell.toggleAgentDock();
}
</script>

<template>
  <div
    v-if="!shell.agentDockCollapsed"
    ref="dockRef"
    class="region region-right-dock agent-dock"
    :class="{ 'agent-dock--resizing': resizing }"
  >
    <div
      class="agent-dock__resize-handle"
      title="Drag to resize the agent dock. Double-click to reset."
      aria-hidden="true"
      @mousedown="startDockResize"
      @dblclick="resetDockWidth"
    >
      <span class="agent-dock__resize-grip" />
    </div>

    <header class="agent-dock__header agent-dock__header--compact">
      <div class="agent-dock__head-row">
        <div class="agent-dock__head-main">
          <AgentDockWorkspaceMenu />
          <div class="agent-dock__head-pills" aria-label="Runtime attention">
            <span v-if="shell.primaryActiveRun" class="agent-dock__pill agent-dock__pill--run">
              Run · {{ runPhaseTag(shell.primaryActiveRun.phase) }}
            </span>
            <span v-if="shell.pendingApprovalsCount" class="agent-dock__pill agent-dock__pill--approvals">
              {{ shell.pendingApprovalsCount }} approval{{ shell.pendingApprovalsCount === 1 ? '' : 's' }}
            </span>
            <span v-if="signalCount" class="agent-dock__pill agent-dock__pill--signals">
              {{ signalCount }} signal{{ signalCount === 1 ? '' : 's' }}
            </span>
          </div>
        </div>
        <button
          type="button"
          class="agent-dock__collapse"
          aria-label="Collapse agent dock"
          @click="collapseDock"
        >
          ×
        </button>
      </div>
    </header>

    <section class="agent-dock__thread">
      <div class="agent-dock__transcript">
        <ConversationSeamPanel />
      </div>
    </section>

    <footer class="agent-dock__composer">
      <AgentDockComposer />
    </footer>
  </div>

  <button
    v-else
    ref="dockRef"
    type="button"
    class="region region-right-dock agent-dock-reopen"
    aria-label="Expand agent dock"
    @click="shell.toggleAgentDock()"
  >
    AGENT
  </button>
</template>
