<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';

import IdeActivityBar from '../ide/IdeActivityBar.vue';
import IdeAttentionPanel from '../ide/IdeAttentionPanel.vue';
import IdeBriefingPanel from '../ide/IdeBriefingPanel.vue';
import IdeExplorerPanel from '../ide/IdeExplorerPanel.vue';
import IdeTeamPanel from '../ide/IdeTeamPanel.vue';
import KairoSidebarPanel from '../ide/KairoSidebarPanel.vue';
import AttentionStackPanel from './AttentionStackPanel.vue';
import KairoVoiceDeckPanel from './KairoVoiceDeckPanel.vue';
import WorkspaceAddForm from './WorkspaceAddForm.vue';
import WorkspaceIcon from '../WorkspaceIcon.vue';
import WorkbenchIcon from '../WorkbenchIcon.vue';
import HudHoloPanelShell from '../../features/hud-holo/HudHoloPanelShell.vue';
import type { HudHoloTone } from '../../features/hud-holo/hud-holo-tones';
import {
  workspaceDisplayLabel,
} from '../../lib/operator-workspace-catalog';
import {
  workspaceIconKind,
} from '../../lib/mockup-workspace-icons';
import { workspaceStatusLine } from '../../lib/mockup-shell-view';
import { isActiveRun } from '../../stores/shell-run-selection';
import {
  clampSidebarWidth,
  MIN_SIDEBAR_WIDTH,
  readStoredSidebarWidth,
  SIDEBAR_WIDTH_KEY,
} from '../../lib/sidebar-width-split';
import { useShellStore } from '../../stores/shell';
import {
  resolveIdeSidebarWidthPx,
} from '../../lib/ide-layout-prefs';
import { useVerticalPanelResize } from '../../composables/useVerticalPanelResize';

const shell = useShellStore();
const workspaceFilter = ref('');
const showAddWorkspaceForm = ref(false);
const sidebarRef = ref<HTMLElement | null>(null);
const expandedSidebarWidth = ref(readStoredSidebarWidth() ?? 280);
const resizing = ref(false);
const {
  panelSize: voiceCardHeight,
  userSized: voiceCardUserSized,
  resizing: voiceCardResizing,
  ariaValueMin: voiceCardHeightMin,
  ariaValueMax: voiceCardHeightMax,
  resetSize: resetVoiceCardHeight,
  startResize: startVoiceCardResize,
  onResizeKeydown: onVoiceCardResizeKeydown,
} = useVerticalPanelResize({
  rootRef: sidebarRef,
  cssVariable: '--voice-card-height',
  storageKey: 'axon-shell-voice-card-height',
  // Auto-height until the operator drags; this is the initial resize target.
  defaultSize: (height) => Math.min(Math.round(height * 0.38), 280),
  minSize: 152,
  maxSize: (height) => Math.round(height * 0.55),
});

const {
  panelSize: ideKairoPanelHeight,
  userSized: ideKairoPanelUserSized,
  resizing: ideKairoPanelResizing,
  ariaValueMin: ideKairoPanelHeightMin,
  ariaValueMax: ideKairoPanelHeightMax,
  resetSize: resetIdeKairoPanelHeight,
  startResize: startIdeKairoPanelResize,
  onResizeKeydown: onIdeKairoPanelResizeKeydown,
} = useVerticalPanelResize({
  rootRef: sidebarRef,
  cssVariable: '--ide-kairo-panel-height',
  storageKey: 'axon-shell-ide-kairo-panel-height',
  defaultSize: (height) => Math.min(Math.round(height * 0.42), 360),
  minSize: 200,
  maxSize: (height) => Math.round(height * 0.7),
});

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
    if (!isActiveRun(run)) {
      continue;
    }
    const workspaceId = run.workspace_id;
    counts[workspaceId] = (counts[workspaceId] ?? 0) + 1;
  }
  return counts;
});

const showSidebarModeToggle = computed(() => shell.layoutMode === 'operator');
const isIdeMode = computed(() => shell.layoutMode === 'ide');
const workspacesHoloTone = computed<HudHoloTone>(() =>
  shell.leftSidebarAttentionBadgeCount > 0 ? 'attention' : 'nominal',
);

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

function syncShellSidebarWidth(): void {
  const shellRoot = sidebarRef.value?.closest('.console-shell--mockup') as HTMLElement | null;
  const width = resolveIdeSidebarWidthPx({
    layoutMode: shell.layoutMode,
    explorerCollapsed: shell.ideExplorerCollapsed,
    expandedSidebarWidth: expandedSidebarWidth.value,
    viewportWidth: window.innerWidth,
  });

  if (!(shell.layoutMode === 'ide' && shell.ideExplorerCollapsed)) {
    expandedSidebarWidth.value = width;
  }

  shellRoot?.style.setProperty('--shell-left-sidebar-width', `${width}px`);
}

function persistSidebarWidth(): void {
  sessionStorage.setItem(SIDEBAR_WIDTH_KEY, String(expandedSidebarWidth.value));
}

function startSidebarResize(event: MouseEvent): void {
  if (event.button !== 0) {
    return;
  }

  event.preventDefault();
  resizing.value = true;

  const startX = event.clientX;
  const startWidth = expandedSidebarWidth.value;

  const onMove = (moveEvent: MouseEvent): void => {
    const shellRoot = sidebarRef.value?.closest('.console-shell--mockup') as HTMLElement | null;
    const rightDockWidth =
      shellRoot?.querySelector('.region-right-dock')?.getBoundingClientRect().width ?? 0;
    const centerMinimum = Math.min(320, Math.max(220, window.innerWidth * 0.28));
    const maximumWithCenter = Math.max(
      MIN_SIDEBAR_WIDTH,
      window.innerWidth - rightDockWidth - centerMinimum - 32,
    );
    const clamped = Math.min(
      clampSidebarWidth(startWidth + (moveEvent.clientX - startX), window.innerWidth),
      maximumWithCenter,
    );
    expandedSidebarWidth.value = clamped;
    shellRoot?.style.setProperty('--shell-left-sidebar-width', `${clamped}px`);
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
  syncShellSidebarWidth();
});

watch(
  () =>
    [
      shell.layoutMode,
      shell.ideExplorerCollapsed,
      shell.leftSidebarMode,
      shell.ideActivityView,
    ] as const,
  () => {
    syncShellSidebarWidth();
  },
);

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
      'left-sidebar-mockup--voice-resizing': voiceCardResizing,
      'left-sidebar-mockup--voice-user-sized': voiceCardUserSized,
      'left-sidebar-mockup--ide-kairo-resizing': ideKairoPanelResizing,
      'left-sidebar-mockup--ide-kairo-user-sized': ideKairoPanelUserSized,
      'left-sidebar-mockup--ide': isIdeMode,
      'left-sidebar-mockup--explorer-collapsed': isIdeMode && shell.ideExplorerCollapsed,
      'left-sidebar-mockup--galaxy': shell.operatorBrainGalaxyActive,
    }"
  >
    <template v-if="isIdeMode">
      <div class="left-sidebar-mockup__ide-body">
        <IdeActivityBar />
        <div class="left-sidebar-mockup__ide-main">
          <IdeAttentionPanel v-if="shell.ideAttentionPanelOpen" />
          <IdeBriefingPanel v-else-if="shell.ideBriefingPanelOpen" />
          <IdeTeamPanel v-else-if="shell.ideActivityView === 'team'" />
          <IdeExplorerPanel v-else />
        </div>
      </div>
      <div
        class="ide-kairo-panel-resize-handle"
        role="separator"
        aria-orientation="horizontal"
        aria-label="Resize agent card"
        title="Drag up/down to resize agent card. Enter or double-click to reset."
        tabindex="0"
        :aria-valuemin="ideKairoPanelHeightMin"
        :aria-valuemax="ideKairoPanelHeightMax"
        :aria-valuenow="ideKairoPanelHeight"
        @mousedown="startIdeKairoPanelResize"
        @keydown="onIdeKairoPanelResizeKeydown"
        @dblclick="resetIdeKairoPanelHeight"
      >
        <span class="ide-kairo-panel-resize-grip" aria-hidden="true" />
      </div>
      <div class="left-sidebar-mockup__status-anchor left-sidebar-mockup__status-anchor--ide">
        <KairoSidebarPanel />
      </div>
    </template>

    <template v-else>
      <HudHoloPanelShell
        class="left-sidebar-mockup__workspaces-panel"
        label="workspaces"
        :tone="workspacesHoloTone"
      >
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
                <span class="workspace-list__name">{{ workspaceDisplayLabel(workspace) }}</span>
                <span
                  v-if="workspace.display_name && workspace.display_name !== workspace.workspace_id"
                  class="workspace-list__meta workspace-list__meta--id"
                >
                  {{ workspace.workspace_id }}
                </span>
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

          <WorkspaceAddForm
            v-if="showAddWorkspaceForm"
            @registered="showAddWorkspaceForm = false"
            @cancel="showAddWorkspaceForm = false"
          />
          <button
            v-else
            type="button"
            class="workspace-new-button"
            @click="showAddWorkspaceForm = true"
          >
            + New Workspace
          </button>
          <p v-if="shell.workspacesError" class="region-copy">{{ shell.workspacesError }}</p>
        </div>

        <AttentionStackPanel
          v-show="shell.leftSidebarMode === 'attention'"
          variant="sidebar"
        />
      </HudHoloPanelShell>
    </template>

    <div
      v-if="!isIdeMode && shell.operatorBrainGalaxyActive && shell.leftSidebarMode === 'workspaces'"
      class="left-sidebar-mockup__status-anchor left-sidebar-mockup__status-anchor--galaxy"
    >
      <AttentionStackPanel variant="sidebar" sections="run-only" />
    </div>

    <div
      v-else-if="!isIdeMode && !shell.operatorBrainGalaxyActive"
      class="left-sidebar-mockup__status-anchor"
    >
      <div
        class="voice-card-resize-handle"
        role="separator"
        aria-orientation="horizontal"
        aria-label="Resize Voice card"
        title="Drag or use arrow keys to resize. Enter or double-click to reset."
        tabindex="0"
        :aria-valuemin="voiceCardHeightMin"
        :aria-valuemax="voiceCardHeightMax"
        :aria-valuenow="voiceCardHeight"
        @mousedown="startVoiceCardResize"
        @keydown="onVoiceCardResizeKeydown"
        @dblclick="resetVoiceCardHeight"
      >
        <span class="voice-card-resize-grip" aria-hidden="true" />
      </div>
      <KairoVoiceDeckPanel />
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
