<script setup lang="ts">
import { computed } from 'vue';

import CommandSeamPanel from '../CommandSeamPanel.vue';
import ConversationSeamPanel from '../ConversationSeamPanel.vue';
import { runPhaseTag } from '../../lib/mockup-shell-view';
import AgentDockWorkspaceTabs from './AgentDockWorkspaceTabs.vue';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

const signalCount = computed(
  () => shell.operatorBriefing?.top_signals.length ?? shell.runtimeSummary?.signals.open_count ?? 0,
);
const workspaceLabel = computed(() => shell.currentWorkspace?.workspace_id ?? 'No workspace selected');
const dockPresenceLabel = computed(() =>
  shell.runtimeSummary?.watch.connected ? 'Live runtime connected' : 'Live runtime unavailable',
);

function collapseDock(): void {
  shell.toggleAgentDock();
}
</script>

<template>
  <div
    v-if="!shell.agentDockCollapsed"
    class="region region-right-dock agent-dock"
  >
    <header class="agent-dock__header">
      <div class="agent-dock__brand-row">
        <div class="agent-dock__brand-copy">
          <p class="agent-dock__eyebrow">Agent</p>
          <p class="agent-dock__title">{{ workspaceLabel }}</p>
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
      <p class="agent-dock__subtitle">{{ dockPresenceLabel }}</p>
      <AgentDockWorkspaceTabs />
    </header>

    <div class="agent-dock__attention-rail" aria-label="Runtime attention">
      <span v-if="shell.primaryActiveRun" class="agent-dock__pill agent-dock__pill--run">
        Run · {{ runPhaseTag(shell.primaryActiveRun.phase) }}
      </span>
      <span v-if="shell.pendingApprovalsCount" class="agent-dock__pill agent-dock__pill--approvals">
        {{ shell.pendingApprovalsCount }} approval{{ shell.pendingApprovalsCount === 1 ? '' : 's' }}
      </span>
      <span v-if="signalCount" class="agent-dock__pill agent-dock__pill--signals">
        {{ signalCount }} signal{{ signalCount === 1 ? '' : 's' }}
      </span>
      <button
        v-if="shell.primaryActiveRun && (shell.canStopPrimaryRun || shell.primaryActiveRun.phase === 'executing')"
        type="button"
        class="agent-dock__stop"
        :disabled="!shell.canStopPrimaryRun && shell.primaryActiveRun.phase !== 'executing'"
        @click="shell.stopPrimaryRun()"
      >
        {{ shell.runMutationState === 'stopping' ? 'Stopping…' : 'Stop' }}
      </button>
    </div>

    <section class="agent-dock__thread">
      <div class="agent-dock__section-header">
        <p class="agent-dock__section-title">Conversation</p>
        <span class="agent-dock__section-meta">{{ shell.threadStateLabel }}</span>
      </div>
      <div class="agent-dock__transcript">
        <ConversationSeamPanel />
      </div>
    </section>

    <footer class="agent-dock__composer">
      <div class="agent-dock__composer-shell">
        <div class="agent-dock__composer-meta">
          <span class="agent-dock__composer-hint">{{ shell.commandSeamHint }}</span>
          <span class="agent-dock__composer-shortcut">Ctrl/Cmd+Enter to send</span>
        </div>
        <CommandSeamPanel :compact="true" />
      </div>
    </footer>
  </div>

  <button
    v-else
    type="button"
    class="region region-right-dock agent-dock-reopen"
    aria-label="Expand agent dock"
    @click="shell.toggleAgentDock()"
  >
    AGENT
  </button>
</template>
