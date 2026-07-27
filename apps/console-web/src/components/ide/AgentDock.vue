<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import ConversationSeamPanel from '../ConversationSeamPanel.vue';
import { useRightDockResize } from '../../composables/useRightDockResize';
import { useVerticalPanelResize } from '../../composables/useVerticalPanelResize';
import {
  agentDockCollapseTitle,
  agentDockReopenAlive,
  agentDockReopenAriaLabel,
  agentDockReopenEmployeeFailure,
  agentDockReopenEmployeeInterrupted,
  agentDockReopenTitle,
} from '../../lib/agent-dock-reopen-view';
import AgentDockComposer from './AgentDockComposer.vue';
import AgentDockThreadTabbar from './AgentDockThreadTabbar.vue';
import AgentDockWorkspaceMenu from './AgentDockWorkspaceMenu.vue';
import IdeAgentReviewStrip from './IdeAgentReviewStrip.vue';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const dockRef = ref<HTMLElement | null>(null);

const reopenState = computed(() => ({
  streaming: shell.agentStreamActive,
  pendingApprovals: shell.pendingApprovalsCount,
  runPhase: shell.primaryActiveRun?.phase ?? null,
  employeeFailureLine: shell.activeIdeEmployeeFailureLine,
  employeeShiftInterrupted: shell.activeIdeEmployeeShiftInterrupted,
  speaking: shell.kairoSpeechActive,
}));

const dockAlive = computed(() => agentDockReopenAlive(reopenState.value));

const dockEmployeeFailure = computed(() =>
  agentDockReopenEmployeeFailure(reopenState.value),
);

const dockEmployeeInterrupted = computed(() =>
  agentDockReopenEmployeeInterrupted(reopenState.value),
);

const reopenTitle = computed(() => agentDockReopenTitle(reopenState.value));
const reopenAriaLabel = computed(() => agentDockReopenAriaLabel(reopenState.value));

// Keep dock width sync / persistence; the vertical edge grip is intentionally omitted.
useRightDockResize({
  dockRef,
  collapsed: computed(() => shell.agentDockCollapsed),
});

const {
  panelSize: composerHeight,
  userSized: composerUserSized,
  resizing: composerResizing,
  ariaValueMin: composerHeightMin,
  ariaValueMax: composerHeightMax,
  resetSize: resetComposerHeight,
  startResize: startComposerResize,
  onResizeKeydown: onComposerResizeKeydown,
} = useVerticalPanelResize({
  rootRef: dockRef,
  cssVariable: '--agent-dock-composer-height',
  storageKey: 'axon-shell-agent-dock-composer-height',
  defaultSize: (height) => Math.min(Math.round(height * 0.34), 280),
  minSize: 160,
  maxSize: (height) => Math.round(height * 0.62),
  growsUp: true,
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
  // Bootstrap already hydrates IDE chat; only retry here when the dock mounts before
  // bootstrap finished and the conversation is still empty.
  if (workspaceId && shell.layoutMode === 'ide' && shell.threadMessages.length === 0) {
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
      'agent-dock--composer-resizing': composerResizing,
      'agent-dock--composer-user-sized': composerUserSized,
      'agent-dock--alive': dockAlive,
      'agent-dock--streaming': shell.agentStreamActive,
    }"
  >
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

    <div
      class="agent-dock__composer-resize-handle"
      role="separator"
      aria-orientation="horizontal"
      aria-label="Resize agent composer"
      title="Drag the top of the composer up or down. Double-click to reset."
      tabindex="0"
      :aria-valuemin="composerHeightMin"
      :aria-valuemax="composerHeightMax"
      :aria-valuenow="composerHeight"
      @mousedown="startComposerResize"
      @keydown="onComposerResizeKeydown"
      @dblclick="resetComposerHeight"
    >
      <span class="agent-dock__composer-resize-grip" aria-hidden="true" />
    </div>

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
      'agent-dock-reopen--alive':
        dockAlive && !dockEmployeeFailure && !dockEmployeeInterrupted,
      'agent-dock-reopen--streaming': shell.agentStreamActive,
      'agent-dock-reopen--approvals': shell.pendingApprovalsCount > 0,
      'agent-dock-reopen--executing': shell.primaryActiveRun?.phase === 'executing',
      'agent-dock-reopen--review-ready': shell.primaryActiveRun?.phase === 'review_ready',
      'agent-dock-reopen--failure': dockEmployeeFailure,
      'agent-dock-reopen--interrupted': dockEmployeeInterrupted,
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
      v-else-if="dockEmployeeInterrupted"
      class="agent-dock-reopen__pulse agent-dock-reopen__pulse--interrupted"
      aria-hidden="true"
    />
    <span
      v-else-if="dockEmployeeFailure"
      class="agent-dock-reopen__pulse agent-dock-reopen__pulse--failure"
      aria-hidden="true"
    />
    <span
      v-else-if="dockAlive"
      class="agent-dock-reopen__pulse"
      aria-hidden="true"
    />
  </button>
</template>
