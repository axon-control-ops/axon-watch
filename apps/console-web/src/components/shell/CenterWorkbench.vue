<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';

import WorkbenchIcon from '../WorkbenchIcon.vue';
import EditorHost from '../EditorHost.vue';
import OperatorStatusRadarPanel from './OperatorStatusRadarPanel.vue';
import TerminalHost from '../TerminalHost.vue';
import {
  clampWorkbenchTerminalHeight,
  persistWorkbenchTerminalPanelVisible,
  readStoredWorkbenchTerminalHeight,
  readStoredWorkbenchTerminalPanelVisible,
  resolveDefaultWorkbenchTerminalHeight,
  WORKBENCH_TERMINAL_HEIGHT_KEY,
} from '../../lib/workbench-terminal-split';
import {
  computeHeroDockHeight,
  computeShellColumnMinHeight,
  isShellLayoutGeometrySane,
  readShellFooterGapPx,
} from '../../lib/shell-column-layout';
import { useShellStore } from '../../stores/shell';
import { renderAgentMessageMarkdown } from '../../lib/agent-message-markdown';
import {
  persistEditorMarkdownPreviewEnabled,
  resolveEditorMarkdownPreviewEnabled,
} from '../../lib/editor-markdown-preview-prefs';
import {
  editorDocumentResourcePath,
  editorTabLabelForDocument,
  editorTabLabelsForDocuments,
} from '../../lib/editor-tab-labels';
import {
  buildEditorBreadcrumbTrail,
  type EditorBreadcrumbSegment,
} from '../../lib/editor-breadcrumb-view';
import {
  persistEditorMinimapEnabled,
  readEditorMinimapEnabled,
} from '../../lib/editor-surface-prefs';
import { terminalSessionTabLabel } from '../../lib/terminal-session-view';
import {
  extractIdeAgentEditSummaries,
  resolveActiveIdeAgentMessage,
  shouldShowIdeAgentCenterPanel,
} from '../../lib/ide-agent-center-view';
import IdeAgentCenterPanel from '../ide/IdeAgentCenterPanel.vue';

const shell = useShellStore();
const hideOperatorEditor = computed(() => shell.layoutMode === 'operator');
const isIdeMode = computed(() => shell.layoutMode === 'ide');
const workbenchLayoutMode = computed((): 'operator' | 'ide' =>
  hideOperatorEditor.value ? 'operator' : 'ide',
);
const terminalPanelVisible = ref(true);
const showTerminalDock = computed(() => terminalPanelVisible.value);
type BottomTabId = 'terminal' | 'problems' | 'output' | 'logs';
const bottomTab = ref<BottomTabId>('terminal');
const workbenchRef = ref<HTMLElement | null>(null);
const terminalHostRef = ref<InstanceType<typeof TerminalHost> | null>(null);
const terminalHeight = ref(240);
const resizing = ref(false);
const terminalHeightCustomized = ref(false);
const editorCursorLine = ref(1);
const editorCursorColumn = ref(1);
const editorMinimapEnabled = ref(readEditorMinimapEnabled());

const problemItems = computed(() => {
  const items: string[] = [];
  if (shell.fileSaveError) items.push(`Save failed: ${shell.fileSaveError}`);
  if (shell.workspaceFilesError) items.push(`Workspace files: ${shell.workspaceFilesError}`);
  if (shell.commandMutationError) items.push(`Command: ${shell.commandMutationError}`);
  if (shell.runMutationError) items.push(`Run: ${shell.runMutationError}`);
  if (shell.runtimeSummaryError) items.push(`Runtime summary: ${shell.runtimeSummaryError}`);
  if (shell.briefingError) items.push(`Briefing: ${shell.briefingError}`);
  if (shell.runsError) items.push(`Runs: ${shell.runsError}`);
  if (shell.inboxError) items.push(`Inbox: ${shell.inboxError}`);
  return items;
});

function createTerminalSession(): void {
  void shell.createTerminalSession();
}

function selectTerminalSession(sessionId: string): void {
  shell.setActiveTerminalSession(sessionId);
}

const activeTerminalSession = computed(() => shell.activeTerminalSession);

const bottomTabs = computed(() => [
  { id: 'terminal' as const, label: 'TERMINAL' },
  { id: 'problems' as const, label: `PROBLEMS ${problemItems.value.length}` },
  { id: 'output' as const, label: 'OUTPUT' },
  { id: 'logs' as const, label: 'LOGS' },
]);

const editorBreadcrumbSegments = computed((): EditorBreadcrumbSegment[] => {
  const workspace = shell.currentWorkspace?.workspace_id ?? 'workspace_smoke';
  const document = shell.activeEditorDocument;
  if (!document) {
    return buildEditorBreadcrumbTrail({
      workspaceId: workspace,
      filePath: 'README.md',
      content: '',
      cursorLine: editorCursorLine.value,
      language: 'markdown',
    });
  }

  const filePath =
    document.source === 'file' && document.filePath
      ? document.filePath
      : editorDocumentResourcePath(document);

  return buildEditorBreadcrumbTrail({
    workspaceId: workspace,
    filePath,
    content: activeEditorValue.value,
    cursorLine: editorCursorLine.value,
    language: document.language,
  });
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

const activeEditorValue = computed(() => shell.activeEditorDocument?.value ?? '');
const editorLineCount = computed(() => {
  const value = activeEditorValue.value;
  return value.length === 0 ? 1 : value.split(/\r\n|\r|\n/).length;
});
const editorEol = computed(() => (activeEditorValue.value.includes('\r\n') ? 'CRLF' : 'LF'));
const editorLanguageLabel = computed(() => {
  const language = shell.activeEditorDocument?.language ?? 'plaintext';
  const labels: Record<string, string> = {
    markdown: 'Markdown',
    json: 'JSON',
    plaintext: 'Plain Text',
    typescript: 'TypeScript',
    javascript: 'JavaScript',
    python: 'Python',
    shell: 'Shell',
  };
  return labels[language] ?? language;
});
const editorAccessLabel = computed(() => {
  if (!shell.activeEditorDocument) {
    return 'No document';
  }
  if (shell.activeEditorDocument.readOnly) {
    return 'Read-only';
  }
  return shell.activeEditorDocument.dirty ? 'Unsaved' : 'Saved';
});
const isMarkdownEditorDocument = computed(
  () => shell.activeEditorDocument?.language === 'markdown',
);
const reviewReadyRunCount = computed(
  () =>
    shell.runs.filter(
      (run) =>
        run.phase === 'review_ready' &&
        run.workspace_id === shell.currentWorkspace?.workspace_id,
    ).length,
);
const activeAgentMessage = computed(() =>
  resolveActiveIdeAgentMessage(
    shell.threadMessages,
    shell.agentStreamActive,
    shell.agentStreamMessageId,
  ),
);
const activeAgentEditCount = computed(() => {
  const message = activeAgentMessage.value;
  if (!message) {
    return 0;
  }
  return extractIdeAgentEditSummaries(message.content, message.message_id).length;
});
const showIdeAgentCenter = computed(() =>
  shouldShowIdeAgentCenterPanel({
    layoutMode: shell.layoutMode,
    agentStreamActive: shell.agentStreamActive,
    composerAgentBusy: shell.composerAgentBusy,
    reviewReadyCount: reviewReadyRunCount.value,
    editedFileCount: activeAgentEditCount.value,
  }),
);
const editorPreviewEnabled = ref(false);

watch(
  () => shell.activeEditorDocument?.id,
  (documentId) => {
    if (!documentId) {
      editorPreviewEnabled.value = false;
      return;
    }
    editorPreviewEnabled.value = resolveEditorMarkdownPreviewEnabled(
      documentId,
      shell.activeEditorDocument?.language === 'markdown',
      shell.activeEditorDocument?.source === 'draft',
    );
  },
  { immediate: true },
);

const editorPreviewHtml = computed(() => {
  if (!isMarkdownEditorDocument.value) {
    return '';
  }
  return renderAgentMessageMarkdown(activeEditorValue.value);
});

function setEditorPreviewMode(enabled: boolean): void {
  const documentId = shell.activeEditorDocument?.id;
  if (!documentId || !isMarkdownEditorDocument.value) {
    return;
  }
  editorPreviewEnabled.value = enabled;
  persistEditorMarkdownPreviewEnabled(documentId, enabled);
}

const editorTabDocuments = computed(() =>
  shell.editorDocuments.filter((document) => document.source === 'file' || document.source === 'draft'),
);
const editorTabLabels = computed(() => editorTabLabelsForDocuments(editorTabDocuments.value));

function editorTabLabel(documentId: string, document: { title: string }): string {
  return editorTabLabelForDocument(
    editorTabDocuments.value.find((entry) => entry.id === documentId) ?? {
      id: documentId,
      title: document.title,
      language: 'markdown',
      value: '',
      description: '',
      source: 'draft',
    },
    editorTabLabels.value,
  );
}
const outputLines = computed(() => {
  const document = shell.activeEditorDocument;
  return [
    document ? `Document · ${document.title}` : 'Document · none',
    document ? `Source · ${document.source}` : '',
    document ? `Access · ${document.readOnly ? 'read-only' : 'editable'}` : '',
    `Workspace · ${shell.currentWorkspace?.workspace_id ?? 'none'}`,
    `Runtime · ${shell.runtimeStateLabel}`,
    `Conversation · ${shell.threadStateLabel}`,
    shell.fileSaveState === 'saving' ? 'Save state · saving' : 'Save state · idle',
  ].filter(Boolean);
});
const logLines = computed(() => {
  if (shell.runHistoryRows.length > 0) {
    return shell.runHistoryRows.map((row) => row.label);
  }
  return [shell.runStateLabel, shell.inboxStateLabel];
});

function handleEditorCursorChange(position: { line: number; column: number }): void {
  editorCursorLine.value = position.line;
  editorCursorColumn.value = position.column;
}

function handleEditorTabClose(event: MouseEvent, documentId: string): void {
  event.stopPropagation();
  shell.closeEditorDocument(documentId);
}

function handleBreadcrumbSegmentClick(segment: EditorBreadcrumbSegment): void {
  if (segment.revealLine) {
    shell.revealEditorLine(segment.revealLine);
  }
}

function toggleEditorMinimap(): void {
  editorMinimapEnabled.value = !editorMinimapEnabled.value;
  persistEditorMinimapEnabled(editorMinimapEnabled.value);
}

function syncTerminalHeightToContainer(): void {
  const container = workbenchRef.value;
  if (!container) {
    return;
  }

  const containerHeight = container.getBoundingClientRect().height;
  const preferredHeight = terminalHeightCustomized.value
    ? terminalHeight.value
    : resolveDefaultWorkbenchTerminalHeight(containerHeight, workbenchLayoutMode.value);
  terminalHeight.value = clampWorkbenchTerminalHeight(preferredHeight, containerHeight);
}

function persistTerminalHeight(): void {
  terminalHeightCustomized.value = true;
  sessionStorage.setItem(WORKBENCH_TERMINAL_HEIGHT_KEY, String(terminalHeight.value));
}

function persistTerminalPanelVisible(visible: boolean): void {
  persistWorkbenchTerminalPanelVisible(workbenchLayoutMode.value, visible);
}

function hideTerminalPanel(): void {
  if (!terminalPanelVisible.value) {
    return;
  }

  terminalPanelVisible.value = false;
  persistTerminalPanelVisible(false);
  requestAnimationFrame(() => runLayoutSync('resize'));
}

watch(
  () => shell.ideTerminalRevealToken,
  () => {
    showTerminalPanel();
  },
);

watch(
  () => shell.ideTerminalToggleToken,
  () => {
    if (!isIdeMode.value) {
      return;
    }
    if (terminalPanelVisible.value) {
      hideTerminalPanel();
    } else {
      showTerminalPanel();
    }
  },
);

function showTerminalPanel(): void {
  if (terminalPanelVisible.value) {
    return;
  }

  terminalPanelVisible.value = true;
  bottomTab.value = 'terminal';
  persistTerminalPanelVisible(true);
  syncTerminalHeightToContainer();
  requestAnimationFrame(() => runLayoutSync('resize'));
}

function toggleTerminalPanel(): void {
  if (terminalPanelVisible.value) {
    hideTerminalPanel();
    return;
  }
  showTerminalPanel();
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
  const shellRoot = workbench?.closest('.console-shell') ?? null;
  if (!workbench || !statusBar || !shellRoot) {
    return;
  }

  const statusTop = statusBar.getBoundingClientRect().top;
  const footerGapPx = readShellFooterGapPx(shellRoot);
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

  terminalPanelVisible.value = readStoredWorkbenchTerminalPanelVisible(workbenchLayoutMode.value);

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
    terminalPanelVisible.value = readStoredWorkbenchTerminalPanelVisible(workbenchLayoutMode.value);
    syncTerminalHeightToContainer();
    runLayoutSync('resize');
  },
);

watch(
  () => shell.activeEditorDocumentId,
  () => {
    editorCursorLine.value = 1;
    editorCursorColumn.value = 1;
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
      'center-workbench--terminal-collapsed': !terminalPanelVisible,
    }"
  >
    <section
      v-if="!hideOperatorEditor"
      class="center-workbench__editor-stack center-workbench__editor-stack--surface"
      :class="{ 'center-workbench__editor-stack--agent-active': showIdeAgentCenter }"
    >
      <IdeAgentCenterPanel v-if="showIdeAgentCenter" class="center-workbench__agent-panel" />

      <div
        class="center-workbench__editor-pane"
        :class="{ 'center-workbench__editor-pane--split': showIdeAgentCenter }"
      >
        <div class="editor-tabbar editor-tabbar--mockup">
        <div class="editor-tabbar__tabs">
          <div
            v-for="document in editorTabDocuments"
            :key="document.id"
            role="tab"
            class="editor-tabbar__tab hud-active-chip hud-active-chip--tab"
            :class="{
              'editor-tabbar__tab--active hud-active-chip--active': shell.activeEditorDocumentId === document.id,
              'editor-tabbar__tab--dirty': document.dirty,
            }"
            :aria-selected="shell.activeEditorDocumentId === document.id"
          >
            <button
              type="button"
              class="editor-tabbar__tab-select"
              @click="shell.setActiveEditorDocument(document.id)"
            >
              <WorkbenchIcon name="file" />
              <span class="editor-tabbar__label">{{ editorTabLabel(document.id, document) }}</span>
              <span
                v-if="document.dirty"
                class="editor-tabbar__dirty-dot"
                aria-label="Unsaved changes"
                title="Unsaved changes"
              />
            </button>
            <button
              type="button"
              class="editor-tabbar__close"
              title="Close editor tab"
              aria-label="Close editor tab"
              @click="handleEditorTabClose($event, document.id)"
            >
              <WorkbenchIcon name="close" class="editor-tabbar__close-icon" />
            </button>
          </div>
        </div>
        <div class="editor-tabbar__tools">
          <div
            v-if="isMarkdownEditorDocument"
            class="conversation-seam__markdown-mode-toggle editor-tabbar__markdown-toggle"
            role="group"
            aria-label="Editor markdown view mode"
          >
            <button
              type="button"
              class="conversation-seam__markdown-mode-button"
              :class="{ 'conversation-seam__markdown-mode-button--active': editorPreviewEnabled }"
              :aria-pressed="editorPreviewEnabled"
              @click="setEditorPreviewMode(true)"
            >
              Preview
            </button>
            <button
              type="button"
              class="conversation-seam__markdown-mode-button"
              :class="{ 'conversation-seam__markdown-mode-button--active': !editorPreviewEnabled }"
              :aria-pressed="!editorPreviewEnabled"
              @click="setEditorPreviewMode(false)"
            >
              Raw
            </button>
          </div>
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

      <nav class="editor-breadcrumb editor-breadcrumb--mockup" aria-label="Editor location">
        <template v-for="(segment, index) in editorBreadcrumbSegments" :key="segment.id">
          <span v-if="index > 0" class="editor-breadcrumb__sep" aria-hidden="true">›</span>
          <button
            type="button"
            class="editor-breadcrumb__segment"
            :class="{
              'editor-breadcrumb__segment--symbol': segment.kind === 'symbol',
              'editor-breadcrumb__segment--active': index === editorBreadcrumbSegments.length - 1,
            }"
            :disabled="!segment.revealLine"
            @click="handleBreadcrumbSegmentClick(segment)"
          >
            <WorkbenchIcon
              v-if="segment.kind === 'file' || segment.kind === 'symbol'"
              name="file"
              :size="12"
            />
            <span>{{ segment.label }}</span>
          </button>
        </template>
      </nav>

      <section
        class="center-workbench__editor"
        :class="{ 'center-workbench__editor--markdown-preview': isMarkdownEditorDocument && editorPreviewEnabled }"
      >
        <EditorHost
          v-if="shell.activeEditorDocument && (!isMarkdownEditorDocument || !editorPreviewEnabled)"
          variant="mockup"
          :title="shell.activeEditorDocument.title"
          :value="shell.activeEditorDocument.value"
          :language="shell.activeEditorDocument.language"
          :description="shell.activeEditorDocument.description"
          :read-only="shell.activeEditorDocument.readOnly"
          :dirty="shell.activeEditorDocument.dirty"
          :minimap-enabled="editorMinimapEnabled"
          :reveal-request="shell.editorRevealRequest"
          @cursor-change="handleEditorCursorChange"
          @selection-change="shell.setEditorSelection"
          @value-change="shell.updateActiveFileContent"
          @save="shell.saveActiveFileDocument"
        />
        <div
          v-else-if="shell.activeEditorDocument && isMarkdownEditorDocument && editorPreviewEnabled"
          class="editor-markdown-preview conversation-seam__content conversation-seam__content--markdown"
          v-html="editorPreviewHtml"
        />
        <div class="editor-statusbar editor-statusbar--mockup">
          <button
            v-if="isIdeMode && !terminalPanelVisible"
            type="button"
            class="editor-statusbar__panel-toggle"
            title="Show terminal panel (Ctrl/Cmd+J)"
            aria-label="Show terminal panel"
            @click="showTerminalPanel"
          >
            TERMINAL
          </button>
          <div class="editor-statusbar__meta">
            <button
              type="button"
              class="editor-statusbar__toggle"
              :class="{ 'editor-statusbar__toggle--active': editorMinimapEnabled }"
              title="Toggle minimap"
              aria-label="Toggle minimap"
              @click="toggleEditorMinimap"
            >
              Minimap
            </button>
            <span>Ln {{ editorCursorLine }}, Col {{ editorCursorColumn }}</span>
            <span>{{ editorLineCount }} line{{ editorLineCount === 1 ? '' : 's' }}</span>
            <span>Spaces: 2</span>
            <span>UTF-8</span>
            <span>{{ editorEol }}</span>
            <span>{{ editorLanguageLabel }}</span>
            <span class="editor-statusbar__state">{{ editorAccessLabel }}</span>
          </div>
        </div>
      </section>
      </div>
    </section>

    <OperatorStatusRadarPanel
      v-if="hideOperatorEditor"
      :terminal-visible="terminalPanelVisible"
      @toggle-terminal="toggleTerminalPanel"
    />

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
            <button type="button" class="terminal-tabbar__action-button" title="New terminal" aria-label="New terminal" @click="createTerminalSession">
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
              type="button"
              class="terminal-tabbar__action-button"
              :title="hideOperatorEditor ? 'Hide terminal panel' : 'Close terminal panel (Ctrl/Cmd+J)'"
              :aria-label="hideOperatorEditor ? 'Hide terminal panel' : 'Close terminal panel'"
              @click="hideTerminalPanel"
            >
              <WorkbenchIcon name="close" class="terminal-tabbar__action" />
            </button>
          </div>
        </div>

        <div v-if="bottomTab === 'terminal'" class="center-workbench__terminal-body">
          <div class="terminal-session-tabs" role="tablist" aria-label="Terminal sessions">
            <button
              v-for="session in shell.terminalSessions"
              :key="session.id"
              type="button"
              role="tab"
              class="terminal-session-tabs__tab"
              :class="{
                'terminal-session-tabs__tab--active': shell.activeTerminalSessionId === session.id,
                'terminal-session-tabs__tab--agent': session.role === 'agent',
              }"
              :aria-selected="shell.activeTerminalSessionId === session.id"
              @click="selectTerminalSession(session.id)"
            >
              {{ terminalSessionTabLabel({
                session_id: session.id,
                workspace_id: shell.currentWorkspace?.workspace_id ?? '',
                role: session.role,
                title: session.title,
                run_id: session.runId,
                created_at: '',
              }) }}
            </button>
          </div>
          <TerminalHost
            ref="terminalHostRef"
            variant="mockup"
            :workspace-id="shell.currentWorkspace?.workspace_id ?? null"
            :session-id="activeTerminalSession.id"
            :session-role="activeTerminalSession.role"
            :run-summary="
              shell.primaryActiveRun
                ? `${shell.primaryActiveRun.run_id} · ${shell.primaryActiveRun.phase} · ${shell.primaryActiveRun.status}`
                : null
            "
            :primary-signal-id="shell.workspacePrimarySignal?.signal_id ?? null"
            :runtime-connected="Boolean(shell.runtimeSummary?.watch.connected)"
          />
        </div>
        <div v-else-if="bottomTab === 'problems'" class="center-workbench__panel-surface">
          <p v-if="problemItems.length === 0" class="center-workbench__panel-empty region-copy">
            No active problems. Runtime, save, briefing, and run surfaces are clear.
          </p>
          <ul v-else class="center-workbench__panel-list">
            <li v-for="item in problemItems" :key="item" class="center-workbench__panel-item center-workbench__panel-item--problem">
              {{ item }}
            </li>
          </ul>
        </div>
        <div v-else-if="bottomTab === 'output'" class="center-workbench__panel-surface">
          <ul class="center-workbench__panel-list">
            <li v-for="item in outputLines" :key="item" class="center-workbench__panel-item">
              {{ item }}
            </li>
          </ul>
        </div>
        <div v-else class="center-workbench__panel-surface">
          <ul class="center-workbench__panel-list">
            <li v-for="item in logLines" :key="item" class="center-workbench__panel-item center-workbench__panel-item--log">
              {{ item }}
            </li>
          </ul>
        </div>
      </section>
    </div>
  </main>
</template>
