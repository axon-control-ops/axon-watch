<script setup lang="ts">
import type {
  IdeEditorStatusAgentChip,
  IdeEditorStatusConnectorChip,
  IdeEditorStatusTerminalChip,
} from '../../lib/ide-editor-status-view';

defineProps<{
  terminalChip: IdeEditorStatusTerminalChip | null;
  connectorChip: IdeEditorStatusConnectorChip | null;
  agentChip: IdeEditorStatusAgentChip | null;
}>();

const emit = defineEmits<{
  showTerminal: [];
  openConnectors: [];
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
        'editor-statusbar__panel-toggle--connector-warning': connectorChip.tone === 'warning',
        'editor-statusbar__panel-toggle--connector-glance': connectorChip.id === 'connector-glance',
      }"
      :title="connectorChip.title"
      :aria-label="connectorChip.ariaLabel"
      @click="emit('openConnectors')"
    >
      {{ connectorChip.label }}
    </button>
    <button
      v-if="agentChip"
      type="button"
      class="editor-statusbar__panel-toggle editor-statusbar__panel-toggle--agent"
      :class="{
        'editor-statusbar__panel-toggle--agent-alive':
          agentChip.alive && !agentChip.failure && !agentChip.interrupted,
        'editor-statusbar__panel-toggle--agent-streaming': agentChip.streaming,
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
