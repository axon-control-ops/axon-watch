<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, useId } from 'vue';

import WorkspaceIcon from '../WorkspaceIcon.vue';
import WorkspaceAddForm from './WorkspaceAddForm.vue';
import { useWorkspaceAgents } from '../../features/workspace-agents/use-workspace-agents';
import { workspaceAgentLabel } from '../../features/workspace-agents/workspace-agent-label';
import { floatingPanelPlacement } from '../../lib/floating-menu-position';
import { workspaceIconKind } from '../../lib/mockup-workspace-icons';
import {
  visibleWorkspacePickerEntries,
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
// The panel is teleported to <body>. `.region-topbar` sets position:relative +
// z-index:50 AND (via mockup-shell premium polish) backdrop-filter, each of
// which creates a stacking context -- so an in-place dropdown could never
// paint above the agent dock/threads rail, whose composer overlay sits at
// z-index 120. No z-index on a descendant can escape an ancestor's stacking
// context, so the panel leaves the topbar entirely and is positioned from the
// trigger's viewport rect instead.
const panelRef = ref<HTMLElement | null>(null);
const panelStyle = ref<Record<string, string>>({});
// Teleporting the panel to <body> puts it far from its trigger in DOM order,
// so the implicit adjacency a screen reader would otherwise rely on is gone.
// aria-controls restores that link explicitly.
const panelId = useId();

const DEFAULT_PANEL_WIDTH_PX = 216;

function updatePanelPosition(): void {
  const trigger = menuRef.value;
  if (!trigger) {
    return;
  }
  const rect = trigger.getBoundingClientRect();
  const placement = floatingPanelPlacement(
    { right: rect.right, bottom: rect.bottom },
    panelRef.value?.offsetWidth || DEFAULT_PANEL_WIDTH_PX,
    { width: window.innerWidth, height: window.innerHeight },
  );
  panelStyle.value = {
    position: 'fixed',
    top: `${placement.top}px`,
    left: `${placement.left}px`,
    right: 'auto',
    maxHeight: `${placement.maxHeight}px`,
  };
}

async function openMenu(): Promise<void> {
  menuOpen.value = true;
  await nextTick();
  updatePanelPosition();
}

function closeMenu(): void {
  menuOpen.value = false;
  showAddWorkspaceForm.value = false;
}

function handleReposition(): void {
  if (menuOpen.value) {
    updatePanelPosition();
  }
}

function handleKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape' && menuOpen.value) {
    closeMenu();
  }
}

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

const visibleWorkspaces = computed(() =>
  visibleWorkspacePickerEntries(shell.workspaces, currentWorkspaceId.value),
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
  if (menuOpen.value) {
    closeMenu();
    return;
  }
  void openMenu();
  void loadWorkspaceAgents({ reason: 'menu-open' });
}

function selectWorkspace(workspaceId: string): void {
  shell.setCurrentWorkspace(workspaceId);
  closeMenu();
}

function openAddWorkspaceForm(event: MouseEvent): void {
  event.stopPropagation();
  showAddWorkspaceForm.value = true;
}

function handleDocumentClick(event: MouseEvent): void {
  const target = event.target;
  if (!(target instanceof Node)) {
    closeMenu();
    return;
  }
  // The panel is teleported out of menuRef, so it must be tested separately --
  // without this, every click inside the open panel counted as an outside
  // click and dismissed the menu before the row could be selected.
  if (menuRef.value?.contains(target) || panelRef.value?.contains(target)) {
    return;
  }
  closeMenu();
}

onMounted(() => {
  document.addEventListener('click', handleDocumentClick);
  document.addEventListener('keydown', handleKeydown);
  window.addEventListener('resize', handleReposition);
  // Capture phase: the trigger can move with any scrolling ancestor, not just
  // the window.
  window.addEventListener('scroll', handleReposition, true);
});

onUnmounted(() => {
  document.removeEventListener('click', handleDocumentClick);
  document.removeEventListener('keydown', handleKeydown);
  window.removeEventListener('resize', handleReposition);
  window.removeEventListener('scroll', handleReposition, true);
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
      :aria-controls="menuOpen ? panelId : undefined"
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

    <Teleport to="body">
    <div
      v-if="menuOpen"
      :id="panelId"
      ref="panelRef"
      class="workspace-picker-menu__panel workspace-picker-menu__panel--floating"
      :class="{ 'workspace-picker-menu__panel--compact': compact }"
      :style="panelStyle"
      role="listbox"
      aria-label="Workspaces"
    >
      <button
        v-for="workspace in visibleWorkspaces"
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
    </Teleport>
  </div>
</template>
