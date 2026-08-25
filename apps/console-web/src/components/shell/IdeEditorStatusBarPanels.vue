<script setup lang="ts">
import type {
  IdeEditorStatusAgentChip,
  IdeEditorStatusConnectorChip,
  IdeEditorStatusGitChip,
  IdeEditorStatusProblemsChip,
  IdeEditorStatusSearchChip,
  IdeEditorStatusTeamChip,
  IdeEditorStatusTerminalChip,
} from '../../lib/ide-editor-status-view';

defineProps<{
  terminalChip: IdeEditorStatusTerminalChip | null;
  connectorChip: IdeEditorStatusConnectorChip | null;
  gitChip: IdeEditorStatusGitChip | null;
  searchChip: IdeEditorStatusSearchChip | null;
  teamChip: IdeEditorStatusTeamChip | null;
  problemsChip: IdeEditorStatusProblemsChip | null;
  agentChip: IdeEditorStatusAgentChip | null;
}>();

const emit = defineEmits<{
  showTerminal: [];
  openConnectors: [];
  openSourceControl: [];
  openSearch: [];
  openTeam: [];
  showProblems: [];
  showAgent: [];
}>();
</script>

<template>
  <div class="editor-statusbar__panel-toggles">
    <button
      v-if="terminalChip"
      type="button"
      class="editor-statusbar__panel-toggle editor-statusbar__panel-toggle--terminal"
      :class="{
        'editor-statusbar__panel-toggle--terminal-alive': terminalChip.showPulse,
        'editor-statusbar__panel-toggle--terminal-executing': terminalChip.executing,
        'editor-statusbar__panel-toggle--terminal-review-ready': terminalChip.reviewReady,
      }"
      :title="terminalChip.title"
      :aria-label="terminalChip.ariaLabel"
      @click="emit('showTerminal')"
    >
      {{ terminalChip.label }}
      <span
        v-if="terminalChip.showPulse"
        class="editor-statusbar__panel-pulse"
        aria-hidden="true"
      />
    </button>
    <button
      v-if="connectorChip"
      type="button"
      class="editor-statusbar__panel-toggle editor-statusbar__panel-toggle--connector"
      :class="{
        'editor-statusbar__panel-toggle--connector-required-alert':
          connectorChip.id === 'connector-required-alert',
        'editor-statusbar__panel-toggle--connector-watch-offline':
          connectorChip.id === 'watch-offline',
        'editor-statusbar__panel-toggle--connector-glance': connectorChip.id === 'connector-glance',
      }"
      :title="connectorChip.title"
      :aria-label="connectorChip.ariaLabel"
      @click="emit('openConnectors')"
    >
      <span
        v-if="connectorChip.id === 'connector-required-alert'"
        class="editor-statusbar__panel-icon editor-statusbar__panel-icon--connector-required-alert"
        aria-hidden="true"
      />
      <span
        v-else-if="connectorChip.id === 'watch-offline'"
        class="editor-statusbar__panel-icon editor-statusbar__panel-icon--watch-offline"
        aria-hidden="true"
      />
      {{ connectorChip.label }}
    </button>
    <button
      v-if="gitChip"
      type="button"
      class="editor-statusbar__panel-toggle editor-statusbar__panel-toggle--git-unsaved"
      :title="gitChip.title"
      :aria-label="gitChip.ariaLabel"
      @click="emit('openSourceControl')"
    >
      {{ gitChip.label }}
    </button>
    <button
      v-if="searchChip"
      type="button"
      class="editor-statusbar__panel-toggle editor-statusbar__panel-toggle--search-error"
      :title="searchChip.title"
      :aria-label="searchChip.ariaLabel"
      @click="emit('openSearch')"
    >
      {{ searchChip.label }}
    </button>
    <button
      v-if="problemsChip"
      type="button"
      class="editor-statusbar__panel-toggle editor-statusbar__panel-toggle--problems"
      :title="problemsChip.title"
      :aria-label="problemsChip.ariaLabel"
      @click="emit('showProblems')"
    >
      {{ problemsChip.label }}
    </button>
    <button
      v-if="teamChip"
      type="button"
      class="editor-statusbar__panel-toggle editor-statusbar__panel-toggle--team"
      :class="{
        'editor-statusbar__panel-toggle--team-failure': teamChip.tone === 'failure',
        'editor-statusbar__panel-toggle--team-interrupted': teamChip.tone === 'interrupted',
        'editor-statusbar__panel-toggle--team-mixed': teamChip.tone === 'mixed',
      }"
      :title="teamChip.title"
      :aria-label="teamChip.ariaLabel"
      @click="emit('openTeam')"
    >
      {{ teamChip.label }}
    </button>
    <button
      v-if="agentChip"
      type="button"
      class="editor-statusbar__panel-toggle editor-statusbar__panel-toggle--agent"
      :class="{
        'editor-statusbar__panel-toggle--agent-alive':
          agentChip.alive && !agentChip.failure && !agentChip.interrupted,
        'editor-statusbar__panel-toggle--agent-streaming': agentChip.streaming,
        'editor-statusbar__panel-toggle--agent-speaking': agentChip.speaking,
        'editor-statusbar__panel-toggle--agent-approvals': agentChip.approvals,
        'editor-statusbar__panel-toggle--agent-executing': agentChip.executing,
        'editor-statusbar__panel-toggle--agent-review-ready': agentChip.reviewReady,
        'editor-statusbar__panel-toggle--agent-failure': agentChip.failure,
        'editor-statusbar__panel-toggle--agent-interrupted': agentChip.interrupted,
      }"
      :title="agentChip.title"
      :aria-label="agentChip.ariaLabel"
      @click="emit('showAgent')"
    >
      {{ agentChip.label }}
      <span
        v-if="agentChip.showBadge !== null"
        class="editor-statusbar__panel-badge"
        aria-hidden="true"
      >
        {{ agentChip.showBadge }}
      </span>
      <span
        v-else-if="agentChip.showPulse"
        class="editor-statusbar__panel-pulse"
        :class="{
          'editor-statusbar__panel-pulse--failure': agentChip.failure,
          'editor-statusbar__panel-pulse--interrupted': agentChip.interrupted,
        }"
        aria-hidden="true"
      />
    </button>
  </div>
</template>
