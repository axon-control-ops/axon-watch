<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';

import WorkspaceIcon from '../WorkspaceIcon.vue';
import WorkspaceAddForm from './WorkspaceAddForm.vue';
import { useWorkspaceAgents } from '../../features/workspace-agents/use-workspace-agents';
import { workspaceAgentLabel } from '../../features/workspace-agents/workspace-agent-label';
import { workspaceIconKind } from '../../lib/mockup-workspace-icons';
import {
  workspacePickerMetaLabel,
  workspacePickerPrimaryLabel,
} from '../../lib/workspace-picker-view';
import { useShellStore } from '../../stores/shell';

withDefaults(
  defineProps<{
    /** Compact single-line trigger for TopBar. */
    compact?: boolean;
  }>(),
  { compact: false },
);

const shell = useShellStore();
const menuOpen = ref(false);
const showAddWorkspaceForm = ref(false);
const menuRef = ref<HTMLElement | null>(null);

const currentWorkspaceId = computed(() => shell.currentWorkspace?.workspace_id ?? null);
const {
  currentWorkspaceAgent,
  agentForWorkspace,
  loadWorkspaceAgents,
} = useWorkspaceAgents(currentWorkspaceId);

const currentWorkspace = computed(() => shell.currentWorkspace ?? null);
const currentWorkspaceLabel = computed(() =>
  currentWorkspace.value
    ? workspacePickerPrimaryLabel(currentWorkspace.value)
    : 'No workspace selected',
);
const currentWorkspaceMeta = computed(() => {
  const agentLabel = workspaceAgentLabel(currentWorkspaceAgent.value);
  if (agentLabel) {
    return agentLabel;
  }
  return currentWorkspace.value ? workspacePickerMetaLabel(currentWorkspace.value) : '';
});
const currentWorkspaceKind = computed(() =>
  currentWorkspace.value ? workspaceIconKind(currentWorkspace.value.workspace_id) : 'hex',
);

function workspaceRowMeta(workspaceId: string): string {
  const agentLabel = workspaceAgentLabel(agentForWorkspace(workspaceId));
  if (agentLabel) {
    return agentLabel;
  }
  const workspace = shell.workspaces.find((entry) => entry.workspace_id === workspaceId);
  return workspace ? workspacePickerMetaLabel(workspace) : '';
}

function toggleMenu(event: MouseEvent): void {
  event.stopPropagation();
  const nextOpen = !menuOpen.value;
  menuOpen.value = nextOpen;
  if (nextOpen) {
    void loadWorkspaceAgents({ reason: 'menu-open' });
  }
}

function selectWorkspace(workspaceId: string): void {
  shell.setCurrentWorkspace(workspaceId);
  showAddWorkspaceForm.value = false;
  menuOpen.value = false;
}

function openAddWorkspaceForm(event: MouseEvent): void {
  event.stopPropagation();
  showAddWorkspaceForm.value = true;
}

function handleDocumentClick(event: MouseEvent): void {
  const target = event.target;
  if (target instanceof Node && menuRef.value?.contains(target)) {
    return;
  }
  menuOpen.value = false;
  showAddWorkspaceForm.value = false;
}

onMounted(() => {
  document.addEventListener('click', handleDocumentClick);
});

onUnmounted(() => {
  document.removeEventListener('click', handleDocumentClick);
});
</script>

<template>
  <div
    ref="menuRef"
    class="workspace-picker-menu"
    :class="{ 'workspace-picker-menu--compact': compact }"
  >
    <button
      type="button"
      class="workspace-picker-menu__trigger"
      :class="{ 'workspace-picker-menu__trigger--active': Boolean(currentWorkspace) }"
      :aria-expanded="menuOpen ? 'true' : 'false'"
      aria-haspopup="listbox"
      aria-label="Select workspace"
      :title="currentWorkspaceMeta || currentWorkspaceLabel"
      @click.stop="toggleMenu"
    >
      <span class="workspace-picker-menu__trigger-main">
        <WorkspaceIcon
          class="workspace-picker-menu__icon"
          :kind="currentWorkspaceKind"
          :size="compact ? 13 : 14"
        />
        <span class="workspace-picker-menu__trigger-copy">
          <span class="workspace-picker-menu__label">{{ currentWorkspaceLabel }}</span>
          <span
            v-if="!compact && currentWorkspaceMeta"
            class="workspace-picker-menu__meta"
          >
            {{ currentWorkspaceMeta }}
          </span>
        </span>
      </span>
      <span
        class="workspace-picker-menu__chevron"
        :class="{ 'workspace-picker-menu__chevron--open': menuOpen }"
        aria-hidden="true"
      >
        ▾
      </span>
    </button>

    <div
      v-if="menuOpen"
      class="workspace-picker-menu__panel"
      role="listbox"
      aria-label="Workspaces"
    >
      <button
        v-for="workspace in shell.workspaces"
        :key="workspace.workspace_id"
        type="button"
        role="option"
        class="workspace-picker-menu__item"
        :class="{
          'workspace-picker-menu__item--active':
            shell.currentWorkspace?.workspace_id === workspace.workspace_id,
        }"
        :aria-selected="shell.currentWorkspace?.workspace_id === workspace.workspace_id"
        @click="selectWorkspace(workspace.workspace_id)"
      >
        <span class="workspace-picker-menu__item-main">
          <WorkspaceIcon
            class="workspace-picker-menu__item-icon"
            :kind="workspaceIconKind(workspace.workspace_id)"
            :size="14"
          />
          <span class="workspace-picker-menu__item-copy">
            <span class="workspace-picker-menu__item-label">
              {{ workspacePickerPrimaryLabel(workspace) }}
            </span>
            <span
              v-if="workspaceRowMeta(workspace.workspace_id)"
              class="workspace-picker-menu__item-meta"
            >
              {{ workspaceRowMeta(workspace.workspace_id) }}
            </span>
          </span>
        </span>
        <span
          v-if="shell.currentWorkspace?.workspace_id === workspace.workspace_id"
          class="workspace-picker-menu__item-active-dot"
          aria-hidden="true"
        />
      </button>
      <button
        v-if="!showAddWorkspaceForm"
        type="button"
        class="workspace-picker-menu__item workspace-picker-menu__item--add"
        @click="openAddWorkspaceForm"
      >
        + Add workspace
      </button>
      <div v-else class="workspace-picker-menu__add-form" @click.stop>
        <WorkspaceAddForm
          @registered="selectWorkspace"
          @cancel="showAddWorkspaceForm = false"
        />
      </div>
    </div>
  </div>
</template>
