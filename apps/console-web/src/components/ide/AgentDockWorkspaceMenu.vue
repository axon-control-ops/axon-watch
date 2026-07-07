<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';

import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const menuOpen = ref(false);
const menuRef = ref<HTMLElement | null>(null);

const currentWorkspaceId = computed(
  () => shell.currentWorkspace?.workspace_id ?? 'No workspace selected',
);

function toggleMenu(event: MouseEvent): void {
  event.stopPropagation();
  menuOpen.value = !menuOpen.value;
}

function selectWorkspace(workspaceId: string): void {
  shell.setCurrentWorkspace(workspaceId);
  menuOpen.value = false;
}

function handleDocumentClick(event: MouseEvent): void {
  const target = event.target;
  if (target instanceof Node && menuRef.value?.contains(target)) {
    return;
  }
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
  <div ref="menuRef" class="agent-dock-workspace-menu">
    <button
      type="button"
      class="agent-dock-workspace-menu__trigger"
      :aria-expanded="menuOpen ? 'true' : 'false'"
      aria-haspopup="listbox"
      @click.stop="toggleMenu"
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
