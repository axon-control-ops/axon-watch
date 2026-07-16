<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';

import WorkbenchIcon from '../WorkbenchIcon.vue';
import WorkbenchTerminalDock from '../WorkbenchTerminalDock.vue';
import AgentEditReviewViewer from '../AgentEditReviewViewer.vue';
import EditorHost from '../EditorHost.vue';
import EditorMarkdownToolbar from './EditorMarkdownToolbar.vue';
import OperatorStatusRadarPanel from './OperatorStatusRadarPanel.vue';
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
import { handleMarkdownContainerClick } from '../../lib/markdown-link-click';
import { isImageFilePath } from '../../lib/workspace-file-language';
import { resolveThreadImageUrl } from '../../lib/thread-image-url';
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
  resolveEditorBreadcrumbFilePath,
  type EditorBreadcrumbSegment,
} from '../../lib/editor-breadcrumb-view';
import {
  persistEditorMinimapEnabled,
  readEditorMinimapEnabled,
} from '../../lib/editor-surface-prefs';
import { isAgentEditReviewDocumentId } from '../../lib/ide-agent-edit-review';
import { buildWorkbenchProblemItems } from '../../lib/workbench-problem-items';
import { useEditorPlanBuild } from '../../composables/use-editor-plan-build';

const shell = useShellStore();
const { activePlanId, buildingPlan, buildPlanError, buildActivePlan } = useEditorPlanBuild(shell);
const hideOperatorEditor = computed(() => shell.layoutMode === 'operator');
const isIdeMode = computed(() => shell.layoutMode === 'ide');
const workbenchLayoutMode = computed((): 'operator' | 'ide' =>
  hideOperatorEditor.value ? 'operator' : 'ide',
);
const terminalPanelVisible = ref(false);
const showTerminalDock = computed(() => terminalPanelVisible.value);
const workbenchRef = ref<HTMLElement | null>(null);
const terminalHeight = ref(240);
const resizing = ref(false);
const terminalHeightCustomized = ref(false);
const editorCursorLine = ref(1);
const editorCursorColumn = ref(1);
const editorMinimapEnabled = ref(readEditorMinimapEnabled());
const editorTabsRef = ref<HTMLElement | null>(null);

const problemItems = computed(() => buildWorkbenchProblemItems(shell));

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

  const filePath = resolveEditorBreadcrumbFilePath({
    source: document.source,
    filePath: document.filePath,
    id: document.id,
    title: document.title,
    value: activeEditorValue.value,
    resourcePath: editorDocumentResourcePath(document),
  });

  return buildEditorBreadcrumbTrail({
    workspaceId: workspace,
    filePath,
    content: activeEditorValue.value,
    cursorLine: editorCursorLine.value,
    language: document.language,
  });
});

const activeEditorValue = computed(() => shell.activeEditorDocument?.value ?? '');
const editorLineCount = computed(() => {
  const value = activeEditorValue.value;
  return value.length === 0 ? 1 : value.split(/\r\n|\r|\n/).length;
});
const editorEol = computed(() => (activeEditorValue.value.includes('\r\n') ? 'CRLF' : 'LF'));
const editorLanguageLabel = computed(() => {
  if (isAgentEditReviewDocument.value && !isMarkdownEditorDocument.value) {
    return 'Diff review';
  }
  if (isAgentEditReviewDocument.value && isMarkdownEditorDocument.value) {
    return 'Markdown review';
  }
  const language = shell.activeEditorDocument?.language ?? 'plaintext';
  const labels: Record<string, string> = {
    markdown: 'Markdown',
    json: 'JSON',
    plaintext: 'Plain Text',
    typescript: 'TypeScript',
    javascript: 'JavaScript',
    python: 'Python',
    shell: 'Shell',
    html: 'HTML',
    css: 'CSS',
    image: 'Image',
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
const isImageEditorDocument = computed(() => {
  const document = shell.activeEditorDocument;
  if (!document) {
    return false;
  }
  if (document.language === 'image') {
    return true;
  }
  return document.source === 'file' && isImageFilePath(document.filePath ?? document.title);
});
const isAgentEditReviewDocument = computed(() =>
  isAgentEditReviewDocumentId(shell.activeEditorDocument?.id),
);
/** Green unified-diff viewer — only for non-markdown agent reviews. */
const showAgentDiffReviewViewer = computed(
  () => isAgentEditReviewDocument.value && !isMarkdownEditorDocument.value,
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
  return renderAgentMessageMarkdown(activeEditorValue.value, {
    workspaceId: shell.currentWorkspace?.workspace_id ?? null,
  });
});

const editorImagePreviewUrl = computed(() => {
  const document = shell.activeEditorDocument;
  const workspaceId = shell.currentWorkspace?.workspace_id;
  if (!document || !workspaceId || !isImageEditorDocument.value || document.source !== 'file') {
    return '';
  }
  const filePath = document.filePath ?? document.title;
  return resolveThreadImageUrl(filePath, { workspaceId });
});

function handleEditorPreviewClick(event: MouseEvent): void {
  const baseFilePath =
    shell.activeEditorDocument?.source === 'file'
      ? shell.activeEditorDocument.filePath
      : null;
  handleMarkdownContainerClick(event, {
    openWorkspaceFile: (path) => shell.openWorkspaceFile(path),
    baseFilePath,
  });
}

function setEditorPreviewMode(enabled: boolean): void {
  const documentId = shell.activeEditorDocument?.id;
  if (!documentId || !isMarkdownEditorDocument.value) {
    return;
  }
  editorPreviewEnabled.value = enabled;
  persistEditorMarkdownPreviewEnabled(documentId, enabled);
}

function handleEditorTabsWheel(event: WheelEvent): void {
  const tabs = editorTabsRef.value;
  if (!tabs) {
    return;
  }
  const delta =
    Math.abs(event.deltaX) > Math.abs(event.deltaY) ? event.deltaX : event.deltaY;
  if (delta === 0 || tabs.scrollWidth <= tabs.clientWidth) {
    return;
  }
  event.preventDefault();
  tabs.scrollLeft += delta;
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
    :class="{ 'center-workbench--resizing': resizing, 'center-workbench--operator': hideOperatorEditor, 'center-workbench--terminal-collapsed': !terminalPanelVisible }"
  >
    <section v-if="!hideOperatorEditor" class="center-workbench__editor-stack center-workbench__editor-stack--surface">
      <header class="editor-chrome editor-chrome--mockup">
        <div class="editor-tabbar editor-tabbar--mockup">
          <div
            ref="editorTabsRef"
            class="editor-tabbar__tabs"
            role="tablist"
            aria-label="Open editor tabs"
            @wheel="handleEditorTabsWheel"
          >
            <div
              v-for="document in editorTabDocuments"
              :key="document.id"
              role="tab"
              class="editor-tabbar__tab"
              :class="{
                'editor-tabbar__tab--active': shell.activeEditorDocumentId === document.id,
                'editor-tabbar__tab--dirty': document.dirty,
              }"
              :aria-selected="shell.activeEditorDocumentId === document.id"
            >
              <button
                type="button"
                class="editor-tabbar__tab-select"
                @click="shell.setActiveEditorDocument(document.id)"
              >
                <WorkbenchIcon name="file" class="editor-tabbar__file-icon" />
                <span class="editor-tabbar__label">{{ editorTabLabel(document.id, document) }}</span>
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
          <div class="editor-tabbar__tools" aria-label="Editor actions">
            <button
              type="button"
              class="editor-tabbar__tool-button"
              title="New file"
              aria-label="New file"
              @click="shell.createWorkspaceFile()"
            >
              <WorkbenchIcon name="new-file" class="editor-tabbar__tool" />
            </button>
            <button type="button" class="editor-tabbar__tool-button" title="Split editor" aria-label="Split editor">
              <WorkbenchIcon name="split" class="editor-tabbar__tool" />
            </button>
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
              <span>{{ segment.label }}</span>
            </button>
          </template>
        </nav>
      </header>

      <section class="center-workbench__editor" :class="{ 'center-workbench__editor--markdown-preview': isMarkdownEditorDocument && editorPreviewEnabled }">
        <EditorMarkdownToolbar
          v-if="isMarkdownEditorDocument && shell.activeEditorDocument"
          :preview-enabled="editorPreviewEnabled"
          :plan-id="activePlanId"
          :building-plan="buildingPlan"
          :build-plan-error="buildPlanError"
          :can-build-plan="Boolean(shell.currentWorkspace?.workspace_id)"
          @set-preview="setEditorPreviewMode"
          @build-plan="buildActivePlan"
        />
        <AgentEditReviewViewer
          v-if="shell.activeEditorDocument && showAgentDiffReviewViewer"
          :content="shell.activeEditorDocument.value"
        />
        <EditorHost
          v-else-if="shell.activeEditorDocument && (!isMarkdownEditorDocument || !editorPreviewEnabled) && !isImageEditorDocument"
          :key="shell.activeEditorDocument.id"
          :document-key="shell.activeEditorDocument.id"
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
        <div v-else-if="shell.activeEditorDocument && isImageEditorDocument" class="editor-image-preview">
          <img class="editor-image-preview__img" :src="editorImagePreviewUrl" :alt="shell.activeEditorDocument.title">
        </div>
        <div
          v-else-if="shell.activeEditorDocument && isMarkdownEditorDocument && editorPreviewEnabled"
          class="editor-markdown-preview conversation-seam__content conversation-seam__content--markdown"
          v-html="editorPreviewHtml"
          @click="handleEditorPreviewClick"
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
              v-if="!showAgentDiffReviewViewer"
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
    </section>

    <OperatorStatusRadarPanel v-if="hideOperatorEditor" :terminal-visible="terminalPanelVisible" @toggle-terminal="toggleTerminalPanel" />
    <WorkbenchTerminalDock v-if="showTerminalDock" :hide-operator-editor="hideOperatorEditor" :log-lines="logLines" :output-lines="outputLines" :problem-items="problemItems" :terminal-height="terminalHeight" @hide="hideTerminalPanel" @start-resize="startTerminalResize" />
  </main>
</template>
