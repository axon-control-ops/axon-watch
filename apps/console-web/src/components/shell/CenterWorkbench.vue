<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';

import WorkbenchIcon from '../WorkbenchIcon.vue';
import EditorHost from '../EditorHost.vue';
import OperatorStatusRadarPanel from './OperatorStatusRadarPanel.vue';
import TerminalHost from '../TerminalHost.vue';
import {
  clampWorkbenchTerminalHeight,
  readStoredWorkbenchTerminalHeight,
  readStoredWorkbenchTerminalPanelVisible,
  resolveDefaultWorkbenchTerminalHeight,
  WORKBENCH_TERMINAL_HEIGHT_KEY,
  WORKBENCH_TERMINAL_PANEL_VISIBLE_KEY,
} from '../../lib/workbench-terminal-split';
import {
  computeHeroDockHeight,
  computeShellColumnMinHeight,
  isShellLayoutGeometrySane,
  readShellFooterGapPx,
} from '../../lib/shell-column-layout';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const hideOperatorEditor = computed(() => shell.layoutMode === 'operator');
const isIdeMode = computed(() => shell.layoutMode === 'ide');
const terminalPanelVisible = ref(true);
const showTerminalDock = computed(
  () => !isIdeMode.value || terminalPanelVisible.value,
);
const bottomTab = ref<'terminal' | 'problems' | 'output' | 'logs'>('terminal');
const workbenchRef = ref<HTMLElement | null>(null);
const terminalHostRef = ref<InstanceType<typeof TerminalHost> | null>(null);
const terminalHeight = ref(240);
const resizing = ref(false);
const terminalHeightCustomized = ref(false);

const bottomTabs = [
  { id: 'terminal' as const, label: 'TERMINAL' },
  { id: 'problems' as const, label: 'PROBLEMS 0' },
  { id: 'output' as const, label: 'OUTPUT' },
  { id: 'logs' as const, label: 'LOGS' },
];

const editorBreadcrumb = computed(() => {
  const workspace = shell.currentWorkspace?.workspace_id ?? 'workspace_smoke';
  const file = shell.activeEditorDocument?.title ?? 'README.md';
  return { workspace, file };
});

const workspaceTerminalLabel = computed(() => {
  const workspaceId = shell.currentWorkspace?.workspace_id;
  if (!workspaceId) {
    return 'No workspace selected';
  }
  return shell.runtimeSummary?.watch.connected
    ? `Connected · ${workspaceId}`
    : `Workspace · ${workspaceId}`;
});

function syncTerminalHeightToContainer(): void {
  const container = workbenchRef.value;
  if (!container) {
    return;
  }

  const containerHeight = container.getBoundingClientRect().height;
  const preferredHeight = terminalHeightCustomized.value
    ? terminalHeight.value
    : resolveDefaultWorkbenchTerminalHeight(containerHeight);
  terminalHeight.value = clampWorkbenchTerminalHeight(preferredHeight, containerHeight);
}

function persistTerminalHeight(): void {
  terminalHeightCustomized.value = true;
  sessionStorage.setItem(WORKBENCH_TERMINAL_HEIGHT_KEY, String(terminalHeight.value));
}

function persistTerminalPanelVisible(visible: boolean): void {
  sessionStorage.setItem(WORKBENCH_TERMINAL_PANEL_VISIBLE_KEY, visible ? '1' : '0');
}

function hideTerminalPanel(): void {
  if (!isIdeMode.value || !terminalPanelVisible.value) {
    return;
  }

  terminalPanelVisible.value = false;
  persistTerminalPanelVisible(false);
  requestAnimationFrame(() => runLayoutSync('resize'));
}

function showTerminalPanel(): void {
  if (!isIdeMode.value || terminalPanelVisible.value) {
    return;
  }

  terminalPanelVisible.value = true;
  bottomTab.value = 'terminal';
  persistTerminalPanelVisible(true);
  syncTerminalHeightToContainer();
  requestAnimationFrame(() => runLayoutSync('resize'));
}

function clearTerminalPanel(): void {
  terminalHostRef.value?.clearTerminal();
}

function startTerminalResize(event: MouseEvent): void {
  if (event.button !== 0) {
    return;
  }

  const container = workbenchRef.value;
  if (!container) {
    return;
  }

  event.preventDefault();
  resizing.value = true;

  const startY = event.clientY;
  const startHeight = terminalHeight.value;
  const containerHeight = container.getBoundingClientRect().height;

  const onMove = (moveEvent: MouseEvent): void => {
    const delta = startY - moveEvent.clientY;
    terminalHeight.value = clampWorkbenchTerminalHeight(
      startHeight + delta,
      containerHeight,
    );
  };

  const onUp = (): void => {
    resizing.value = false;
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
    document.removeEventListener('mousemove', onMove);
    document.removeEventListener('mouseup', onUp);
    persistTerminalHeight();
  };

  document.body.style.cursor = 'row-resize';
  document.body.style.userSelect = 'none';
  document.addEventListener('mousemove', onMove);
  document.addEventListener('mouseup', onUp);
}

let resizeObserver: ResizeObserver | undefined;

function syncShellColumnHeights(): void {
  const workbench = workbenchRef.value;
  const statusBar = document.querySelector('.region-status-bar');
  const shell = workbench?.closest('.console-shell') ?? null;
  if (!workbench || !statusBar || !shell) {
    return;
  }

  const statusTop = statusBar.getBoundingClientRect().top;
  const footerGapPx = readShellFooterGapPx(shell);
  const columns = [
    workbench,
    document.querySelector('.region-right-dock'),
    document.querySelector('.region-left-sidebar'),
  ];

  for (const column of columns) {
    if (!(column instanceof HTMLElement)) {
      continue;
    }

    const columnTop = column.getBoundingClientRect().top;
    if (!isShellLayoutGeometrySane(columnTop, statusTop)) {
      continue;
    }

    const target = computeShellColumnMinHeight(columnTop, statusTop, footerGapPx);
    const maxReasonable = window.innerHeight * 1.25;
    if (target <= 0 || target > maxReasonable) {
      continue;
    }

    column.style.minHeight = `${target}px`;
    column.style.height = `${target}px`;
    column.style.maxHeight = `${target}px`;
  }
}

function syncBriefingDockHeight(bottomDock: Element | null): void {
  const dockHeight = bottomDock?.getBoundingClientRect().height ?? 0;
  const heroHeight = computeHeroDockHeight(dockHeight, shell.layoutMode);
  if (heroHeight > 0) {
    document.documentElement.style.setProperty('--briefing-dock-height', `${heroHeight}px`);
  }
}

function runLayoutSync(trigger: 'mount' | 'resize'): void {
  syncShellColumnHeights();
  const bottomDock = workbenchRef.value?.querySelector('.center-workbench__bottom-dock') ?? null;
  syncBriefingDockHeight(bottomDock);
  if (trigger === 'resize') {
    syncTerminalHeightToContainer();
  }
}

onMounted(() => {
  const stored = readStoredWorkbenchTerminalHeight();
  if (stored !== null) {
    terminalHeight.value = stored;
    terminalHeightCustomized.value = true;
  }

  terminalPanelVisible.value = readStoredWorkbenchTerminalPanelVisible();

  syncTerminalHeightToContainer();
  runLayoutSync('mount');
  requestAnimationFrame(() => runLayoutSync('mount'));

  if (workbenchRef.value) {
    resizeObserver = new ResizeObserver(() => {
      runLayoutSync('resize');
    });
    resizeObserver.observe(workbenchRef.value);
    const rightDock = document.querySelector('.region-right-dock');
    if (rightDock) {
      resizeObserver.observe(rightDock);
    }
  }
});

onBeforeUnmount(() => {
  resizeObserver?.disconnect();
});

watch(
  () => shell.layoutMode,
  () => {
    syncTerminalHeightToContainer();
    runLayoutSync('resize');
  },
);
</script>

<template>
  <main
    ref="workbenchRef"
    class="region region-center-workbench center-workbench center-workbench--mockup"
    :class="{
      'center-workbench--resizing': resizing,
      'center-workbench--operator': hideOperatorEditor,
      'center-workbench--ide-terminal-collapsed': isIdeMode && !terminalPanelVisible,
    }"
  >
    <section
      v-if="!hideOperatorEditor"
      class="center-workbench__editor-stack center-workbench__editor-stack--surface"
    >
      <div class="editor-tabbar editor-tabbar--mockup">
        <div class="editor-tabbar__tabs">
          <button
            v-for="document in shell.editorDocuments.filter((doc) => doc.source === 'file')"
            :key="document.id"
            type="button"
            class="editor-tabbar__tab hud-active-chip hud-active-chip--tab"
            :class="{ 'editor-tabbar__tab--active hud-active-chip--active': shell.activeEditorDocumentId === document.id }"
            @click="shell.setActiveEditorDocument(document.id)"
          >
            <WorkbenchIcon name="file" />
            <span class="editor-tabbar__label">{{ document.title }}</span>
            <WorkbenchIcon name="close" class="editor-tabbar__close-icon" />
          </button>
        </div>
        <div class="editor-tabbar__tools">
          <button
            type="button"
            class="editor-tabbar__tool-button"
            title="New file"
            aria-label="New file"
            @click="shell.createWorkspaceFile()"
          >
            <WorkbenchIcon name="new-file" class="editor-tabbar__tool" />
          </button>
          <WorkbenchIcon name="split" class="editor-tabbar__tool" title="Split editor" />
          <WorkbenchIcon name="book" class="editor-tabbar__tool" title="Open changes" />
          <button
            type="button"
            class="editor-tabbar__tool-button"
            title="Rename active file"
            aria-label="Rename active file"
            :disabled="!shell.activeWorkspaceFilePath"
            @click="shell.renameActiveWorkspaceFile()"
          >
            <WorkbenchIcon name="more" class="editor-tabbar__tool" />
          </button>
        </div>
      </div>

      <p class="editor-breadcrumb editor-breadcrumb--mockup">
        <span class="editor-breadcrumb__workspace">{{ editorBreadcrumb.workspace }}</span>
        <span class="editor-breadcrumb__sep" aria-hidden="true">&gt;</span>
        <span class="editor-breadcrumb__file">
          <WorkbenchIcon name="file" :size="12" />
          <span>{{ editorBreadcrumb.file }}</span>
        </span>
      </p>

      <section class="center-workbench__editor">
        <EditorHost
          v-if="shell.activeEditorDocument"
          variant="mockup"
          :title="shell.activeEditorDocument.title"
          :value="shell.activeEditorDocument.value"
          :language="shell.activeEditorDocument.language"
          :description="shell.activeEditorDocument.description"
          :read-only="shell.activeEditorDocument.readOnly"
          :dirty="shell.activeEditorDocument.dirty"
          @value-change="shell.updateActiveFileContent"
          @save="shell.saveActiveFileDocument"
        />
        <div class="editor-statusbar editor-statusbar--mockup">
          <button
            v-if="isIdeMode && !terminalPanelVisible"
            type="button"
            class="editor-statusbar__panel-toggle"
            title="Show terminal panel"
            aria-label="Show terminal panel"
            @click="showTerminalPanel"
          >
            TERMINAL
          </button>
          <div class="editor-statusbar__meta">
            <span>Ln 11, Col 22</span>
            <span>Spaces: 2</span>
            <span>UTF-8</span>
            <span>LF</span>
            <span>Markdown</span>
          </div>
        </div>
      </section>
    </section>

    <OperatorStatusRadarPanel v-if="hideOperatorEditor" />

    <div
      v-if="showTerminalDock"
      class="center-workbench__bottom-dock center-workbench__bottom-dock--surface"
      :style="{ height: `${terminalHeight}px` }"
    >
      <section class="center-workbench__terminal-panel center-workbench__terminal-panel--mockup">
        <div
          class="center-workbench__resize-handle"
          role="separator"
          aria-orientation="horizontal"
          aria-label="Resize terminal panel"
          tabindex="0"
          @mousedown="startTerminalResize"
        >
          <span class="center-workbench__resize-grip" aria-hidden="true" />
        </div>

        <div class="terminal-tabbar terminal-tabbar--mockup">
          <div class="terminal-tabbar__tabs">
            <button
              v-for="tab in bottomTabs"
              :key="tab.id"
              type="button"
              class="terminal-tabbar__tab hud-active-chip hud-active-chip--tab"
              :class="{ 'terminal-tabbar__tab--active hud-active-chip--active': bottomTab === tab.id }"
              @click="bottomTab = tab.id"
            >
              {{ tab.label }}
            </button>
          </div>
          <p class="terminal-tabbar__workspace">
            <span
              class="terminal-tabbar__workspace-dot"
              :class="{
                'terminal-tabbar__workspace-dot--connected': Boolean(
                  shell.runtimeSummary?.watch.connected && shell.currentWorkspace,
                ),
              }"
              aria-hidden="true"
            />
            {{ workspaceTerminalLabel }}
          </p>
          <div class="terminal-tabbar__actions">
            <button type="button" class="terminal-tabbar__action-button" title="New terminal" aria-label="New terminal">
              <WorkbenchIcon name="plus" class="terminal-tabbar__action" />
            </button>
            <button type="button" class="terminal-tabbar__action-button" title="Split terminal" aria-label="Split terminal">
              <WorkbenchIcon name="split" class="terminal-tabbar__action" />
            </button>
            <button
              type="button"
              class="terminal-tabbar__action-button"
              title="Clear terminal"
              aria-label="Clear terminal"
              @click="clearTerminalPanel"
            >
              <WorkbenchIcon name="trash" class="terminal-tabbar__action" />
            </button>
            <button
              v-if="isIdeMode"
              type="button"
              class="terminal-tabbar__action-button"
              title="Close terminal panel"
              aria-label="Close terminal panel"
              @click="hideTerminalPanel"
            >
              <WorkbenchIcon name="close" class="terminal-tabbar__action" />
            </button>
          </div>
        </div>

        <div v-if="bottomTab === 'terminal'" class="center-workbench__terminal-body">
          <TerminalHost
            ref="terminalHostRef"
            variant="mockup"
            :workspace-id="shell.currentWorkspace?.workspace_id ?? null"
            :run-summary="
              shell.primaryActiveRun
                ? `${shell.primaryActiveRun.run_id} · ${shell.primaryActiveRun.phase} · ${shell.primaryActiveRun.status}`
                : null
            "
            :primary-signal-id="shell.workspacePrimarySignal?.signal_id ?? null"
            :runtime-connected="Boolean(shell.runtimeSummary?.watch.connected)"
          />
        </div>
        <p v-else class="center-workbench__terminal-placeholder region-copy">
          {{ bottomTab.toUpperCase() }} surface attaches in a later slice.
        </p>
      </section>
    </div>
  </main>
</template>
