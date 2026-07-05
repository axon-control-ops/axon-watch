<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';

import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const menuOpen = ref(false);

const currentWorkspaceId = computed(
  () => shell.currentWorkspace?.workspace_id ?? 'No workspace selected',
);

function toggleMenu(): void {
  menuOpen.value = !menuOpen.value;
}

function selectWorkspace(workspaceId: string): void {
  shell.setCurrentWorkspace(workspaceId);
  menuOpen.value = false;
}

function handleDocumentClick(): void {
  menuOpen.value = false;
}

onMounted(() => {
  document.addEventListener('click', handleDocumentClick);
});

onUnmounted(() => {
  document.removeEventListener('click', handleDocumentClick);
});
</script>

<template>
  <div class="agent-dock-workspace-menu" @click.stop>
    <button
      type="button"
      class="agent-dock-workspace-menu__trigger"
      :aria-expanded="menuOpen ? 'true' : 'false'"
      aria-haspopup="listbox"
      @click="toggleMenu"
    >
      <span class="agent-dock-workspace-menu__label">{{ currentWorkspaceId }}</span>
      <span
        class="agent-dock-workspace-menu__chevron"
        :class="{ 'agent-dock-workspace-menu__chevron--open': menuOpen }"
        aria-hidden="true"
      >
        ▾
      </span>
    </button>

    <div
      v-if="menuOpen"
      class="agent-dock-workspace-menu__panel"
      role="listbox"
      aria-label="Workspaces"
    >
      <button
        v-for="workspace in shell.workspaces"
        :key="workspace.workspace_id"
        type="button"
        role="option"
        class="agent-dock-workspace-menu__item"
        :class="{
          'agent-dock-workspace-menu__item--active':
            shell.currentWorkspace?.workspace_id === workspace.workspace_id,
        }"
        :aria-selected="shell.currentWorkspace?.workspace_id === workspace.workspace_id"
        @click="selectWorkspace(workspace.workspace_id)"
      >
        {{ workspace.workspace_id }}
      </button>
    </div>
  </div>
</template>
