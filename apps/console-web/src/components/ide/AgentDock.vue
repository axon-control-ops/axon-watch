<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';

import ConversationSeamPanel from '../ConversationSeamPanel.vue';
import { runPhaseTag } from '../../lib/mockup-shell-view';
import {
  AGENT_DOCK_COLLAPSED_WIDTH_PX,
  clampAgentDockWidth,
  defaultAgentDockWidth,
  persistAgentDockWidth,
  readStoredAgentDockWidth,
} from '../../lib/agent-dock-width';
import AgentDockComposer from './AgentDockComposer.vue';
import AgentDockWorkspaceMenu from './AgentDockWorkspaceMenu.vue';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const dockRef = ref<HTMLElement | null>(null);
const agentDockWidth = ref(
  readStoredAgentDockWidth() ?? defaultAgentDockWidth(window.innerWidth),
);
const resizing = ref(false);

const signalCount = computed(
  () => shell.operatorBriefing?.top_signals.length ?? shell.runtimeSummary?.signals.open_count ?? 0,
);

function shellRoot(): HTMLElement | null {
  return dockRef.value?.closest('.console-shell--mockup') as HTMLElement | null;
}

function applyAgentDockWidth(width: number): void {
  const clamped = clampAgentDockWidth(width, window.innerWidth);
  agentDockWidth.value = clamped;
  shellRoot()?.style.setProperty('--shell-agent-dock-width', `${clamped}px`);
}

function applyCollapsedDockWidth(): void {
  shellRoot()?.style.setProperty(
    '--shell-agent-dock-width',
    `${AGENT_DOCK_COLLAPSED_WIDTH_PX}px`,
  );
}

function syncDockWidthToShell(): void {
  if (shell.agentDockCollapsed) {
    applyCollapsedDockWidth();
    return;
  }

  applyAgentDockWidth(agentDockWidth.value);
}

function collapseDock(): void {
  shell.toggleAgentDock();
}

function startAgentDockResize(event: MouseEvent): void {
  if (event.button !== 0 || shell.agentDockCollapsed) {
    return;
  }

  event.preventDefault();
  resizing.value = true;

  const onMove = (moveEvent: MouseEvent): void => {
    applyAgentDockWidth(window.innerWidth - moveEvent.clientX);
  };

  const onUp = (): void => {
    resizing.value = false;
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
    document.removeEventListener('mousemove', onMove);
    document.removeEventListener('mouseup', onUp);
    persistAgentDockWidth(agentDockWidth.value);
  };

  document.body.style.cursor = 'col-resize';
  document.body.style.userSelect = 'none';
  document.addEventListener('mousemove', onMove);
  document.addEventListener('mouseup', onUp);
}

function resetAgentDockWidth(): void {
  applyAgentDockWidth(defaultAgentDockWidth(window.innerWidth));
  persistAgentDockWidth(agentDockWidth.value);
}

onMounted(() => {
  syncDockWidthToShell();
  window.addEventListener('resize', syncDockWidthToShell);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', syncDockWidthToShell);
  if (resizing.value) {
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  }
});

watch(
  () => shell.agentDockCollapsed,
  async () => {
    await nextTick();
    syncDockWidthToShell();
    if (!shell.agentDockCollapsed) {
      persistAgentDockWidth(agentDockWidth.value);
    }
  },
);
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
      @mousedown="startAgentDockResize"
      @dblclick="resetAgentDockWidth"
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
