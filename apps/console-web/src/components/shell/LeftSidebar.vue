<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

import IdeActivityBar from '../ide/IdeActivityBar.vue';
import IdeExplorerPanel from '../ide/IdeExplorerPanel.vue';
import KairoSidebarPanel from '../ide/KairoSidebarPanel.vue';
import AttentionStackPanel from './AttentionStackPanel.vue';
import WorkspaceIcon from '../WorkspaceIcon.vue';
import WorkbenchIcon from '../WorkbenchIcon.vue';
import {
  workspaceIconKind,
  workspaceStatusLine,
} from '../../lib/mockup-shell-view';
import {
  clampSidebarWidth,
  readStoredSidebarWidth,
  SIDEBAR_WIDTH_KEY,
} from '../../lib/sidebar-width-split';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const workspaceFilter = ref('');
const sidebarRef = ref<HTMLElement | null>(null);
const sidebarWidth = ref(readStoredSidebarWidth() ?? 280);
const resizing = ref(false);

const catalogWorkspaces = computed(() => shell.workspaces);

const filteredWorkspaces = computed(() => {
  const query = workspaceFilter.value.trim().toLowerCase();
  if (!query) {
    return catalogWorkspaces.value;
  }
  return catalogWorkspaces.value.filter((workspace) =>
    workspace.workspace_id.toLowerCase().includes(query),
  );
});

const runCountsByWorkspace = computed(() => {
  const counts: Record<string, number> = {};
  for (const run of shell.runs) {
    const workspaceId = run.workspace_id;
    counts[workspaceId] = (counts[workspaceId] ?? 0) + 1;
  }
  return counts;
});

const showSidebarModeToggle = computed(() => shell.layoutMode === 'operator');
const isIdeMode = computed(() => shell.layoutMode === 'ide');

function isActiveWorkspace(workspaceId: string): boolean {
  return shell.currentWorkspace?.workspace_id === workspaceId;
}

function workspaceSubtext(workspaceId: string): string {
  return workspaceStatusLine(
    workspaceId,
    isActiveWorkspace(workspaceId),
    runCountsByWorkspace.value,
  );
}

function applySidebarWidth(width: number): void {
  const shellRoot = sidebarRef.value?.closest('.console-shell--mockup') as HTMLElement | null;
  const clamped = clampSidebarWidth(width, window.innerWidth);
  sidebarWidth.value = clamped;
  shellRoot?.style.setProperty('--shell-left-sidebar-width', `${clamped}px`);
}

function persistSidebarWidth(): void {
  sessionStorage.setItem(SIDEBAR_WIDTH_KEY, String(sidebarWidth.value));
}

function startSidebarResize(event: MouseEvent): void {
  if (event.button !== 0) {
    return;
  }

  event.preventDefault();
  resizing.value = true;

  const startX = event.clientX;
  const startWidth = sidebarWidth.value;

  const onMove = (moveEvent: MouseEvent): void => {
    applySidebarWidth(startWidth + (moveEvent.clientX - startX));
  };

  const onUp = (): void => {
    resizing.value = false;
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
    document.removeEventListener('mousemove', onMove);
    document.removeEventListener('mouseup', onUp);
    persistSidebarWidth();
  };

  document.body.style.cursor = 'col-resize';
  document.body.style.userSelect = 'none';
  document.addEventListener('mousemove', onMove);
  document.addEventListener('mouseup', onUp);
}

onMounted(() => {
  applySidebarWidth(sidebarWidth.value);
});

onBeforeUnmount(() => {
  if (resizing.value) {
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  }
});
</script>

<template>
  <aside
    ref="sidebarRef"
    class="region region-left-sidebar left-sidebar-mockup"
    :class="{
      'left-sidebar-mockup--resizing': resizing,
      'left-sidebar-mockup--ide': isIdeMode,
      'left-sidebar-mockup--explorer-collapsed': isIdeMode && shell.ideExplorerCollapsed,
    }"
  >
    <template v-if="isIdeMode">
      <div class="left-sidebar-mockup__ide-body">
        <IdeActivityBar />
        <div class="left-sidebar-mockup__ide-main">
          <button
            v-if="shell.ideExplorerCollapsed"
            type="button"
            class="left-sidebar-mockup__explorer-reopen"
            aria-label="Expand explorer"
            @click="shell.toggleIdeExplorer()"
          >
            EXPLORER
          </button>
          <IdeExplorerPanel />
        </div>
      </div>
    </template>

    <template v-else>
      <div class="left-sidebar-mockup__workspaces-panel hud-panel-frame">
        <div
          v-if="showSidebarModeToggle"
          class="left-sidebar-mockup__mode-header panel-heading panel-heading--toggle"
        >
          <div class="shell-mode-toggle" role="tablist" aria-label="Left sidebar mode">
            <button
              type="button"
              role="tab"
              class="shell-mode-toggle__button"
              :class="{ 'shell-mode-toggle__button--active': shell.leftSidebarMode === 'workspaces' }"
              :aria-selected="shell.leftSidebarMode === 'workspaces'"
              @click="shell.setLeftSidebarMode('workspaces')"
            >
              Workspaces
            </button>
            <button
              type="button"
              role="tab"
              class="shell-mode-toggle__button shell-mode-toggle__button--attention"
              :class="{
                'shell-mode-toggle__button--active': shell.leftSidebarMode === 'attention',
                'shell-mode-toggle__button--attention-hot': shell.leftSidebarAttentionBadgeCount > 0,
              }"
              :aria-selected="shell.leftSidebarMode === 'attention'"
              @click="shell.setLeftSidebarMode('attention')"
            >
              <span class="shell-mode-toggle__label">Attention</span>
              <span
                v-if="shell.leftSidebarAttentionBadgeCount > 0"
                class="shell-mode-toggle__badge"
                aria-hidden="true"
              >
                {{ shell.leftSidebarAttentionBadgeCount }}
              </span>
            </button>
          </div>
        </div>

        <div
          v-show="shell.leftSidebarMode === 'workspaces'"
          class="left-sidebar-mockup__workspaces"
        >
          <label class="workspace-filter">
            <WorkbenchIcon name="search" :size="13" class="workspace-filter__icon" />
            <input
              v-model="workspaceFilter"
              class="workspace-filter__input"
              type="search"
              placeholder="Filter workspaces..."
            />
          </label>

          <div class="workspace-list workspace-list--mockup">
            <button
              v-for="workspace in filteredWorkspaces"
              :key="workspace.workspace_id"
              type="button"
              class="workspace-list__button workspace-list__button--mockup hud-active-chip hud-active-chip--frame"
              :class="{
                'workspace-list__button--active hud-active-chip--active': isActiveWorkspace(
                  workspace.workspace_id,
                ),
              }"
              @click="shell.setCurrentWorkspace(workspace.workspace_id)"
            >
              <WorkspaceIcon
                class="workspace-list__icon"
                :kind="workspaceIconKind(workspace.workspace_id)"
              />
              <span class="workspace-list__copy">
                <span class="workspace-list__name">{{ workspace.workspace_id }}</span>
                <span
                  class="workspace-list__meta"
                  :class="{
                    'workspace-list__meta--active': isActiveWorkspace(workspace.workspace_id),
                  }"
                >
                  <span
                    v-if="isActiveWorkspace(workspace.workspace_id)"
                    class="workspace-list__status-dot"
                    aria-hidden="true"
                  />
                  {{ workspaceSubtext(workspace.workspace_id) }}
                </span>
              </span>
              <span class="workspace-list__menu" aria-hidden="true">
                <WorkbenchIcon name="more" :size="12" />
              </span>
            </button>
          </div>

          <button type="button" class="workspace-new-button">+ New Workspace</button>
          <p v-if="shell.workspacesError" class="region-copy">{{ shell.workspacesError }}</p>
        </div>

        <AttentionStackPanel
          v-show="shell.leftSidebarMode === 'attention'"
          variant="sidebar"
        />
      </div>
    </template>

    <div class="left-sidebar-mockup__status-anchor">
      <KairoSidebarPanel v-if="isIdeMode" />
      <section v-else class="workspace-status-card hud-panel-frame">
        <p class="workspace-status-card__title">WORKSPACE STATUS</p>
        <div class="workspace-status-card__body">
          <div class="workspace-status-card__radar" aria-hidden="true">
            <span class="workspace-status-card__ring workspace-status-card__ring--outer" />
            <span class="workspace-status-card__ring workspace-status-card__ring--mid" />
            <span class="workspace-status-card__ring workspace-status-card__ring--inner" />
            <span class="workspace-status-card__crosshair workspace-status-card__crosshair--h" />
            <span class="workspace-status-card__crosshair workspace-status-card__crosshair--v" />
            <span class="workspace-status-card__tick workspace-status-card__tick--n" />
            <span class="workspace-status-card__tick workspace-status-card__tick--e" />
            <span class="workspace-status-card__tick workspace-status-card__tick--s" />
            <span class="workspace-status-card__tick workspace-status-card__tick--w" />
            <span class="workspace-status-card__sweep" />
          </div>
          <dl class="workspace-status-card__meta">
            <div v-for="row in shell.workspaceStatusCardRows" :key="row.label">
              <dt>{{ row.label }}</dt>
              <dd>{{ row.value }}</dd>
            </div>
          </dl>
        </div>
      </section>
    </div>

    <div
      class="left-sidebar-mockup__resize-handle"
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize left sidebar"
      tabindex="0"
      @mousedown="startSidebarResize"
    >
      <span class="left-sidebar-mockup__resize-grip" aria-hidden="true" />
    </div>
  </aside>
</template>
