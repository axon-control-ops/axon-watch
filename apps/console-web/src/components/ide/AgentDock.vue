<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import ConversationSeamPanel from '../ConversationSeamPanel.vue';
import { useRightDockResize } from '../../composables/useRightDockResize';
import AgentDockComposer from './AgentDockComposer.vue';
import AgentDockThreadTabbar from './AgentDockThreadTabbar.vue';
import AgentDockWorkspaceMenu from './AgentDockWorkspaceMenu.vue';
import IdeKairoConversationBar from './IdeKairoConversationBar.vue';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const dockRef = ref<HTMLElement | null>(null);

const { resizing, resetDockWidth, startDockResize } = useRightDockResize({
  dockRef,
  collapsed: computed(() => shell.agentDockCollapsed),
});

function collapseDock(): void {
  shell.toggleAgentDock();
}

onMounted(() => {
  if (shell.runtimeStatusLoadState === 'idle') {
    void shell.loadRuntimeStatus();
  }
  if (shell.cursorCatalogLoadState === 'idle') {
    void shell.loadCursorCatalog();
  }
  const workspaceId = shell.currentWorkspace?.workspace_id;
  if (workspaceId) {
    void shell.hydrateWorkspaceIdeChat(workspaceId);
  }
});
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

    <header class="agent-dock__header agent-dock__header--compact agent-dock__header--ide">
      <div class="agent-dock__head-row">
        <div class="agent-dock__head-main">
          <AgentDockWorkspaceMenu />
          <div v-if="shell.pendingApprovalsCount" class="agent-dock__head-pills" aria-label="Agent attention">
            <span v-if="shell.pendingApprovalsCount" class="agent-dock__pill agent-dock__pill--approvals">
              {{ shell.pendingApprovalsCount }} approval{{ shell.pendingApprovalsCount === 1 ? '' : 's' }}
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
      <div class="agent-dock__head-tabs">
        <AgentDockThreadTabbar />
      </div>
    </header>

    <section class="agent-dock__thread">
      <div
        v-if="shell.threadStateLabel"
        class="agent-dock__section-header agent-dock__section-header--compact"
      >
        <p class="agent-dock__section-meta">{{ shell.threadStateLabel }}</p>
      </div>
      <div class="agent-dock__transcript">
        <ConversationSeamPanel />
      </div>
    </section>

    <footer class="agent-dock__composer">
      <IdeKairoConversationBar />
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
