<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import ConversationSeamPanel from '../ConversationSeamPanel.vue';
import { useRightDockResize } from '../../composables/useRightDockResize';
import {
  agentDockCollapseTitle,
  agentDockReopenAlive,
  agentDockReopenAriaLabel,
  agentDockReopenEmployeeFailure,
  agentDockReopenEmployeeInterrupted,
  agentDockReopenTitle,
} from '../../lib/agent-dock-reopen-view';
import { resolveAgentDockStickyPrompt } from '../../lib/agent-dock-sticky-prompt';
import AgentDockComposer from './AgentDockComposer.vue';
import AgentDockStickyPrompt from './agent-dock/AgentDockStickyPrompt.vue';
import AgentDockThreadTabbar from './AgentDockThreadTabbar.vue';
import AgentDockWorkspaceMenu from './AgentDockWorkspaceMenu.vue';
import IdeAgentReviewStrip from './IdeAgentReviewStrip.vue';
import { useShellStore } from '../../stores/shell';
import './agent-dock/agent-dock-sticky-prompt.css';

const shell = useShellStore();
const dockRef = ref<HTMLElement | null>(null);

const stickyOperatorPrompt = computed(() => {
  const text = resolveAgentDockStickyPrompt({
    threadMessages: shell.threadMessages,
    activityPrompt: shell.ideComposerActivity?.operatorPrompt,
  });
  // #region agent log
  if (text) {
    fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Debug-Session-Id': 'bef50e',
      },
      body: JSON.stringify({
        sessionId: 'bef50e',
        runId: 'sticky-prompt',
        hypothesisId: 'S1',
        location: 'AgentDock.vue:stickyOperatorPrompt',
        message: 'sticky prompt resolved',
        data: { length: text.length, preview: text.slice(0, 80) },
        timestamp: Date.now(),
      }),
    }).catch(() => {});
  }
  // #endregion
  return text;
});

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
      <AgentDockStickyPrompt
        v-if="stickyOperatorPrompt"
        :text="stickyOperatorPrompt"
      />
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
