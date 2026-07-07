<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';

import WorkspaceIcon from '../WorkspaceIcon.vue';
import { workspaceIconKind } from '../../lib/mockup-shell-view';
import {
  workspacePickerMetaLabel,
  workspacePickerPrimaryLabel,
} from '../../lib/workspace-picker-view';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const menuOpen = ref(false);
const menuRef = ref<HTMLElement | null>(null);

const currentWorkspace = computed(() => shell.currentWorkspace ?? null);
const currentWorkspaceLabel = computed(() =>
  currentWorkspace.value
    ? workspacePickerPrimaryLabel(currentWorkspace.value)
    : 'No workspace selected',
);
const currentWorkspaceMeta = computed(() =>
  currentWorkspace.value ? workspacePickerMetaLabel(currentWorkspace.value) : '',
);
const currentWorkspaceKind = computed(() =>
  currentWorkspace.value ? workspaceIconKind(currentWorkspace.value.workspace_id) : 'hex',
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
      :class="{ 'agent-dock-workspace-menu__trigger--active': Boolean(currentWorkspace) }"
      :aria-expanded="menuOpen ? 'true' : 'false'"
      aria-haspopup="listbox"
      :title="currentWorkspaceMeta || currentWorkspaceLabel"
      @click.stop="toggleMenu"
    >
      <span class="agent-dock-workspace-menu__trigger-main">
        <WorkspaceIcon
          class="agent-dock-workspace-menu__icon"
          :kind="currentWorkspaceKind"
          :size="14"
        />
        <span class="agent-dock-workspace-menu__label">{{ currentWorkspaceLabel }}</span>
      </span>
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
        <span class="agent-dock-workspace-menu__item-main">
          <WorkspaceIcon
            class="agent-dock-workspace-menu__item-icon"
            :kind="workspaceIconKind(workspace.workspace_id)"
            :size="14"
          />
          <span class="agent-dock-workspace-menu__item-copy">
            <span class="agent-dock-workspace-menu__item-label">
              {{ workspacePickerPrimaryLabel(workspace) }}
            </span>
            <span
              v-if="workspacePickerMetaLabel(workspace)"
              class="agent-dock-workspace-menu__item-meta"
            >
              {{ workspacePickerMetaLabel(workspace) }}
            </span>
          </span>
        </span>
        <span
          v-if="shell.currentWorkspace?.workspace_id === workspace.workspace_id"
          class="agent-dock-workspace-menu__item-active-dot"
          aria-hidden="true"
        />
      </button>
    </div>
  </div>
</template>
