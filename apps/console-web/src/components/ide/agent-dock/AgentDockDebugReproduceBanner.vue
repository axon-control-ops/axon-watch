<script setup lang="ts">
import { computed } from 'vue';

import type { DebugReproduceRequest } from '../../../lib/debug-reproduce-view';
import { useShellStore } from '../../../stores/shell';
import AgentDebugSessionLogPanel from '../AgentDebugSessionLogPanel.vue';

defineProps<{
  request: DebugReproduceRequest;
  pending: boolean;
}>();

const emit = defineEmits<{
  proceed: [];
  dismiss: [];
}>();

const shell = useShellStore();
const workspaceId = computed(() => shell.currentWorkspace?.workspace_id ?? null);
</script>

<template>
  <div class="agent-dock-composer__debug-reproduce-banner" role="status">
    <ol class="agent-dock-composer__debug-reproduce-steps">
      <li v-for="(step, index) in request.steps" :key="index">{{ step }}</li>
    </ol>
    <AgentDebugSessionLogPanel :workspace-id="workspaceId" compact />
    <div class="agent-dock-composer__debug-reproduce-actions">
      <button
        type="button"
        class="agent-dock-composer__debug-reproduce-btn agent-dock-composer__debug-reproduce-btn--proceed"
        :disabled="pending"
        @click="emit('proceed')"
      >
        {{ pending ? 'Sending…' : 'Proceed (Ctrl+Enter)' }}
      </button>
      <button
        type="button"
        class="agent-dock-composer__debug-reproduce-btn agent-dock-composer__debug-reproduce-btn--dismiss"
        :disabled="pending"
        @click="emit('dismiss')"
      >
        Dismiss
      </button>
    </div>
  </div>
</template>
