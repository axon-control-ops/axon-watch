<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import ConversationSeamPanel from '../ConversationSeamPanel.vue';
import { useRightDockResize } from '../../composables/useRightDockResize';
import {
  agentDockCollapseTitle,
  agentDockReopenAlive,
  agentDockReopenAriaLabel,
  agentDockReopenTitle,
} from '../../lib/agent-dock-reopen-view';
import AgentDockComposer from './AgentDockComposer.vue';
import AgentDockThreadTabbar from './AgentDockThreadTabbar.vue';
import AgentDockWorkspaceMenu from './AgentDockWorkspaceMenu.vue';
import IdeAgentReviewStrip from './IdeAgentReviewStrip.vue';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const dockRef = ref<HTMLElement | null>(null);

const dockAlive = computed(() =>
  agentDockReopenAlive({
    streaming: shell.agentStreamActive,
    pendingApprovals: shell.pendingApprovalsCount,
    runPhase: shell.primaryActiveRun?.phase ?? null,
  }),
);

const reopenState = computed(() => ({
  streaming: shell.agentStreamActive,
  pendingApprovals: shell.pendingApprovalsCount,
  runPhase: shell.primaryActiveRun?.phase ?? null,
}));

const reopenTitle = computed(() => agentDockReopenTitle(reopenState.value));
const reopenAriaLabel = computed(() => agentDockReopenAriaLabel(reopenState.value));

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
    :class="{
      'agent-dock--resizing': resizing,
      'agent-dock--alive': dockAlive,
      'agent-dock--streaming': shell.agentStreamActive,
    }"
  >
    <div
      class="agent-dock__resize-handle"
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize agent dock"
      title="Drag or use arrow keys to resize. Enter or double-click to reset."
      tabindex="0"
      :aria-valuemin="ariaValueMin"
      :aria-valuemax="ariaValueMax"
      :aria-valuenow="dockWidth"
      @mousedown="startDockResize"
      @keydown="onDockResizeKeydown"
      @dblclick="resetDockWidth"
    >
      <span class="agent-dock__resize-grip" aria-hidden="true" />
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
          :title="agentDockCollapseTitle()"
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
      <IdeAgentReviewStrip />
      <AgentDockComposer />
    </footer>
  </div>

  <button
    v-else
    ref="dockRef"
    type="button"
    class="region region-right-dock agent-dock-reopen"
    :class="{
      'agent-dock-reopen--alive': dockAlive,
      'agent-dock-reopen--streaming': shell.agentStreamActive,
      'agent-dock-reopen--approvals': shell.pendingApprovalsCount > 0,
      'agent-dock-reopen--executing': shell.primaryActiveRun?.phase === 'executing',
      'agent-dock-reopen--review-ready': shell.primaryActiveRun?.phase === 'review_ready',
    }"
    :aria-label="reopenAriaLabel"
    :title="reopenTitle"
    @click="shell.toggleAgentDock()"
  >
    <span class="agent-dock-reopen__label">AGENT</span>
    <span
      v-if="shell.pendingApprovalsCount > 0"
      class="agent-dock-reopen__badge"
      aria-hidden="true"
    >
      {{ shell.pendingApprovalsCount }}
    </span>
    <span
      v-else-if="dockAlive"
      class="agent-dock-reopen__pulse"
      aria-hidden="true"
    />
  </button>
</template>
