<script setup lang="ts">
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
</script>

<template>
  <div class="agent-dock-workspace-tabs" role="tablist" aria-label="Open workspaces">
    <button
      v-for="workspace in shell.workspaces"
      :key="workspace.workspace_id"
      type="button"
      role="tab"
      class="agent-dock-workspace-tabs__tab"
      :class="{
        'agent-dock-workspace-tabs__tab--active':
          shell.currentWorkspace?.workspace_id === workspace.workspace_id,
      }"
      :aria-selected="shell.currentWorkspace?.workspace_id === workspace.workspace_id"
      @click="shell.setCurrentWorkspace(workspace.workspace_id)"
    >
      {{ workspace.workspace_id }}
    </button>
  </div>
</template>
