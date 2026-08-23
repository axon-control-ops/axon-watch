<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';

import WorkbenchTerminalDock from '../WorkbenchTerminalDock.vue';
import AgentEditReviewViewer from '../AgentEditReviewViewer.vue';
import EditorHost from '../EditorHost.vue';
import GalaxySpeechCaptions from '../../features/brain-galaxy/GalaxySpeechCaptions.vue';
import { shouldShowGalaxySpeechCaptions } from '../../features/brain-galaxy/should-show-galaxy-speech-captions';
import EditorMarkdownToolbar from './EditorMarkdownToolbar.vue';
import EditorCsvToolbar from './EditorCsvToolbar.vue';
import CenterWorkbenchIdeQuickGuide from './CenterWorkbenchIdeQuickGuide.vue';
import CenterWorkbenchEditorChrome from './CenterWorkbenchEditorChrome.vue';
import CenterWorkbenchEditorFooter from './CenterWorkbenchEditorFooter.vue';
import CenterWorkbenchEmptyEditor from './CenterWorkbenchEmptyEditor.vue';
import EditorPdfPreview from './EditorPdfPreview.vue';
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
import { dispatchEditorSurfaceLayoutSync } from '../../lib/editor-surface-layout';
import { useShellStore } from '../../stores/shell';
import { renderAgentMessageMarkdown } from '../../lib/agent-message-markdown';
import { handleMarkdownContainerClick } from '../../lib/markdown-link-click';
import { isBinaryFilePath, isImageFilePath, isPdfFilePath } from '../../lib/workspace-file-language';
import { useEditorCsvPreview } from '../../lib/use-editor-csv-preview';
import { resolveEditorImagePreviewUrl } from '../../lib/thread-image-url';
import { useEditorPdfPreview } from '../../lib/use-editor-pdf-preview';
import { useEditorBreadcrumbSegments } from '../../lib/use-editor-breadcrumb-segments';
import {
  persistEditorMarkdownPreviewEnabled,
  resolveEditorMarkdownPreviewEnabled,
} from '../../lib/editor-markdown-preview-prefs';
import { editorDocumentResourcePath } from '../../lib/editor-tab-labels';
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
import { type IdeQuickGuideActionId } from '../../lib/ide-quick-guide';
import {
  handleIdeQuickGuideAction,
  openIdeSearch,
  openIdeSourceControl,
  openIdeTeam,
  openWatchConnectors,
  useIdeEditorStatusBar,
} from '../../composables/useIdeEditorStatusBar';
import { useIdeQuickGuideSticky } from '../../composables/useIdeQuickGuideSticky';
import { useWorkbenchPanelAutoPeek } from '../../composables/useWorkbenchPanelAutoPeek';
import { useWorkbenchTerminalAutoClose } from '../../composables/useWorkbenchTerminalAutoClose';
import { buildWorkbenchProblemItems } from '../../lib/workbench-problem-items';
import { useEditorPlanBuild } from '../../composables/use-editor-plan-build';
import { useEditorStatusBarMeta } from '../../composables/useEditorStatusBarMeta';
const shell = useShellStore();
const { activePlanId, buildingPlan, buildPlanError, buildActivePlan } = useEditorPlanBuild(shell);
const hideOperatorEditor = computed(() => shell.layoutMode === 'operator');
const isIdeMode = computed(() => shell.layoutMode === 'ide');
const showGalaxySpeechCaptions = computed(() => shouldShowGalaxySpeechCaptions({ layoutMode: shell.layoutMode, operatorBrainGalaxyActive: shell.operatorBrainGalaxyActive }));
const workbenchLayoutMode = computed((): 'operator' | 'ide' =>
  hideOperatorEditor.value ? 'operator' : 'ide',
);
const terminalPanelVisible = ref(false);
const showTerminalDock = computed(() => terminalPanelVisible.value);
const agentDockReopenState = computed(() => ({
  streaming: shell.agentStreamActive,
  pendingApprovals: shell.pendingApprovalsCount,
  runPhase: shell.primaryActiveRun?.phase ?? null,
  employeeFailureLine: shell.activeIdeEmployeeFailureLine,
  employeeShiftInterrupted: shell.activeIdeEmployeeShiftInterrupted,
  speaking: shell.kairoSpeechActive,
}));
const {
  ideEditorStatusTerminalChip,
  ideEditorStatusAgentChip,
  ideEditorStatusConnectorChip,
  ideEditorStatusGitChip,
  ideEditorStatusSearchChip,
  ideEditorStatusTeamChip,
  ideEditorStatusProblemsChip,
  ideQuickGuide,
} = useIdeEditorStatusBar({
  shell,
  workbenchLayoutMode,
  terminalPanelVisible,
  terminalReopenRunPhase: computed(() => shell.primaryActiveRun?.phase ?? null),
  agentDockReopenState,
});

const { ideQuickGuideSticky, dismissIdeQuickGuide } = useIdeQuickGuideSticky(ideQuickGuide);
const workbenchRef = ref<HTMLElement | null>(null);
const terminalHeight = ref(240);
const resizing = ref(false);
const terminalHeightCustomized = ref(false);
const editorCursorLine = ref(1);
const editorCursorColumn = ref(1);
const editorMinimapEnabled = ref(readEditorMinimapEnabled());

const problemItems = computed(() => buildWorkbenchProblemItems(shell));

const activeEditorValue = computed(() => shell.activeEditorDocument?.value ?? '');
const editorBreadcrumbSegments = useEditorBreadcrumbSegments({
  activeDocument: computed(() => shell.activeEditorDocument),
  activeEditorValue,
  workspaceId: computed(() => shell.currentWorkspace?.workspace_id),
  cursorLine: editorCursorLine,
});

const isMarkdownEditorDocument = computed(
  () => shell.activeEditorDocument?.language === 'markdown',
);
const {
  isCsvEditorDocument,
  csvTablePreviewEnabled,
  editorCsvTableHtml,
  setCsvTablePreviewMode,
} = useEditorCsvPreview({
  activeDocument: computed(() => shell.activeEditorDocument),
  activeEditorValue,
});
const isImageEditorDocument = computed(() => {
  const document = shell.activeEditorDocument;
  if (!document) return false;
  if (document.language === 'image') return true;
  return document.source === 'file' && isImageFilePath(document.filePath ?? document.title);
});
const { isPdfEditorDocument, editorPdfPreviewUrl } = useEditorPdfPreview({
  activeDocument: computed(() => shell.activeEditorDocument),
  workspace: computed(() => shell.currentWorkspace),
});
const isBinaryEditorDocument = computed(() => {
  const document = shell.activeEditorDocument;
  if (!document || document.source !== 'file') {
    return false;
  }
  const path = document.filePath ?? document.title;
  return isBinaryFilePath(path) && !isImageFilePath(path) && !isPdfFilePath(path);
});
const isAgentEditReviewDocument = computed(() =>
  isAgentEditReviewDocumentId(shell.activeEditorDocument?.id),
);
/** Green unified-diff viewer — only for non-markdown agent reviews. */
const showAgentDiffReviewViewer = computed(
  () => isAgentEditReviewDocument.value && !isMarkdownEditorDocument.value,
);
const { editorLineCount, editorEol, editorLanguageLabel, editorAccessStatus } =
  useEditorStatusBarMeta({
    activeDocument: computed(() => shell.activeEditorDocument),
    activeEditorValue,
    isAgentEditReviewDocument,
    isMarkdownEditorDocument,
    isBinaryEditorDocument,
    isImageEditorDocument,
  });
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
  const doc = shell.activeEditorDocument;
  const ws = shell.currentWorkspace;
  return resolveEditorImagePreviewUrl({
    workspaceId: ws?.workspace_id, projectRoot: ws?.project_root,
    filePath: doc?.filePath, title: doc?.title, previewUrl: doc?.previewUrl,
    isImageDocument: isImageEditorDocument.value, source: doc?.source,
  });
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

const editorTabDocuments = computed(() =>
  shell.editorDocuments.filter((document) => document.source === 'file' || document.source === 'draft'),
);
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
  const nextHeight = clampWorkbenchTerminalHeight(preferredHeight, containerHeight);
  if (Math.abs(nextHeight - terminalHeight.value) >= 1) {
    terminalHeight.value = nextHeight;
  }
}

function persistTerminalHeight(): void {
  terminalHeightCustomized.value = true;
  sessionStorage.setItem(WORKBENCH_TERMINAL_HEIGHT_KEY, String(terminalHeight.value));
}

function persistTerminalPanelVisible(visible: boolean): void {
  persistWorkbenchTerminalPanelVisible(workbenchLayoutMode.value, visible);
  shell.syncWorkbenchTerminalPanelVisible(visible);
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

function showAgentDock(): void {
  if (!shell.agentDockCollapsed) {
    return;
  }
  // Expand the right dock only — do not swap the left sidebar off Team/Explorer.
  shell.toggleAgentDock();
}

useWorkbenchPanelAutoPeek({
  shell,
  workbenchLayoutMode,
  terminalPanelVisible,
  onShowTerminal: showTerminalPanel,
  onShowAgentDock: showAgentDock,
});
useWorkbenchTerminalAutoClose({ terminalPanelVisible, onHideTerminal: hideTerminalPanel });

function toggleTerminalPanel(): void {
  terminalPanelVisible.value ? hideTerminalPanel() : showTerminalPanel();
}

const onIdeQuickGuideAction = (actionId: IdeQuickGuideActionId): void =>
  handleIdeQuickGuideAction(actionId, { shell, showAgentDock, showTerminalPanel });

const onOpenWatchConnectors = (): void => openWatchConnectors(shell);
const onOpenSourceControl = (): void => openIdeSourceControl(shell);
const onOpenSearch = (): void => openIdeSearch(shell);
const onShowProblems = (): void => shell.revealIdeWorkbenchProblems();
const onOpenExplorer = (): void => shell.focusIdeSidebarView('explorer');
const onCreateNewFile = (): void => shell.requestIdeExplorerInlineCreate('file');

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
let resizeObserverFrame: number | null = null;

function syncShellColumnHeights(): void {
  const workbench = workbenchRef.value;
  const statusBar = document.querySelector('.region-status-bar');
  const shellRoot = workbench?.closest('.console-shell') ?? null;
  if (!workbench || !statusBar || !shellRoot) {
    return;
  }

  const statusTop = statusBar.getBoundingClientRect().top;
  const shellFooterGapPx = readShellFooterGapPx(shellRoot);
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

    const footerGapPx =
      shell.layoutMode === 'ide' && column.classList.contains('region-right-dock')
        ? 0
        : shellFooterGapPx;
    const target = Math.round(computeShellColumnMinHeight(columnTop, statusTop, footerGapPx));
    const maxReasonable = window.innerHeight * 1.25;
    if (target <= 0 || target > maxReasonable) continue;

    const nextHeight = `${target}px`;
    if (
      column.style.minHeight === nextHeight &&
      column.style.height === nextHeight &&
      column.style.maxHeight === nextHeight
    ) continue;
    column.style.minHeight = nextHeight;
    column.style.height = nextHeight;
    column.style.maxHeight = nextHeight;
  }
}

function syncBriefingDockHeight(bottomDock: Element | null): void {
  const dockHeight = bottomDock?.getBoundingClientRect().height ?? 0;
  const heroHeight = computeHeroDockHeight(dockHeight, shell.layoutMode);
  if (heroHeight > 0) {
    const nextHeight = `${heroHeight}px`;
    if (
      document.documentElement.style.getPropertyValue('--briefing-dock-height') !== nextHeight
    ) {
      document.documentElement.style.setProperty('--briefing-dock-height', nextHeight);
    }
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

function scheduleEditorSurfaceLayoutSync(): void {
  runLayoutSync('resize');
  requestAnimationFrame(() => {
    runLayoutSync('resize');
    dispatchEditorSurfaceLayoutSync();
  });
}

function scheduleResizeLayoutSync(): void {
  if (resizeObserverFrame !== null) {
    return;
  }
  resizeObserverFrame = requestAnimationFrame(() => {
    resizeObserverFrame = null;
    runLayoutSync('resize');
  });
}

onMounted(() => {
  const stored = readStoredWorkbenchTerminalHeight();
  if (stored !== null) {
    terminalHeight.value = stored;
    terminalHeightCustomized.value = true;
  }

  terminalPanelVisible.value = readStoredWorkbenchTerminalPanelVisible(workbenchLayoutMode.value);
  shell.syncWorkbenchTerminalPanelVisible(terminalPanelVisible.value);

  syncTerminalHeightToContainer();
  runLayoutSync('mount');
  requestAnimationFrame(() => runLayoutSync('mount'));

  if (workbenchRef.value) {
    resizeObserver = new ResizeObserver(() => {
      // Never write observed geometry from inside the observer callback.
      // Coalesce bursts into one frame to prevent ResizeObserver feedback loops.
      scheduleResizeLayoutSync();
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
  if (resizeObserverFrame !== null) {
    cancelAnimationFrame(resizeObserverFrame);
    resizeObserverFrame = null;
  }
});

watch(
  () => shell.layoutMode,
  () => {
    terminalPanelVisible.value = readStoredWorkbenchTerminalPanelVisible(workbenchLayoutMode.value);
    shell.syncWorkbenchTerminalPanelVisible(terminalPanelVisible.value);
    syncTerminalHeightToContainer();
    scheduleEditorSurfaceLayoutSync();
  },
);

watch(
  () => shell.currentWorkspace?.workspace_id,
  async () => {
    await nextTick();
    scheduleEditorSurfaceLayoutSync();
  },
);

watch(
  () => shell.workspaceFilesLoadState,
  async (state) => {
    if (state !== 'loaded') {
      return;
    }
    await nextTick();
    scheduleEditorSurfaceLayoutSync();
  },
);

watch(
  () => shell.activeEditorDocumentId,
  async () => {
    editorCursorLine.value = 1;
    editorCursorColumn.value = 1;
    await nextTick();
    dispatchEditorSurfaceLayoutSync();
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
      <CenterWorkbenchEditorChrome
        :active-editor-document-id="shell.activeEditorDocumentId"
        :editor-tab-documents="editorTabDocuments"
        :editor-breadcrumb-segments="editorBreadcrumbSegments"
        :active-workspace-file-path="shell.activeWorkspaceFilePath"
        @select-document="shell.setActiveEditorDocument"
        @close-document="shell.closeEditorDocument"
        @create-file="shell.createWorkspaceFile()"
        @rename-file="shell.renameActiveWorkspaceFile()"
        @breadcrumb-click="handleBreadcrumbSegmentClick"
      />

      <section
        class="center-workbench__editor"
        :class="{
          'center-workbench__editor--markdown-preview': isMarkdownEditorDocument && editorPreviewEnabled,
          'center-workbench__editor--csv-table-preview': isCsvEditorDocument && csvTablePreviewEnabled,
        }"
      >
        <CenterWorkbenchIdeQuickGuide
          v-if="ideQuickGuideSticky"
          :guide="ideQuickGuideSticky"
          :with-editor="Boolean(shell.activeEditorDocument)"
          @action="onIdeQuickGuideAction"
          @dismiss="dismissIdeQuickGuide"
        />
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
        <EditorCsvToolbar
          v-if="isCsvEditorDocument && shell.activeEditorDocument"
          :table-enabled="csvTablePreviewEnabled"
          @set-table="setCsvTablePreviewMode"
        />
        <AgentEditReviewViewer
          v-if="shell.activeEditorDocument && showAgentDiffReviewViewer"
          :content="shell.activeEditorDocument.value"
        />
        <CenterWorkbenchEmptyEditor
          v-else-if="!shell.activeEditorDocument"
          :has-workspace="Boolean(shell.currentWorkspace?.workspace_id)"
          @open-explorer="onOpenExplorer"
          @open-search="onOpenSearch"
          @create-new-file="onCreateNewFile"
          @show-agent="showAgentDock"
        />
        <EditorHost
          v-else-if="(!isMarkdownEditorDocument || !editorPreviewEnabled) && (!isCsvEditorDocument || !csvTablePreviewEnabled) && !isImageEditorDocument && !isPdfEditorDocument && !isBinaryEditorDocument"
          :key="shell.activeEditorDocument.id"
          :document-key="shell.activeEditorDocument.id"
          variant="mockup"
          :theme-profile="isIdeMode ? 'cursor' : 'mockup'"
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
        <EditorPdfPreview
          v-else-if="shell.activeEditorDocument && isPdfEditorDocument"
          :title="shell.activeEditorDocument.title"
          :preview-url="editorPdfPreviewUrl"
        />
        <div v-else-if="shell.activeEditorDocument && isBinaryEditorDocument" class="editor-binary-preview">
          <p class="editor-binary-preview__title">{{ shell.activeEditorDocument.title }}</p>
          <p class="editor-binary-preview__body">{{ shell.activeEditorDocument.description }}</p>
        </div>
        <div
          v-else-if="shell.activeEditorDocument && isMarkdownEditorDocument && editorPreviewEnabled"
          class="editor-markdown-preview conversation-seam__content conversation-seam__content--markdown"
          v-html="editorPreviewHtml"
          @click="handleEditorPreviewClick"
        />
        <div
          v-else-if="shell.activeEditorDocument && isCsvEditorDocument && csvTablePreviewEnabled"
          class="editor-csv-preview conversation-seam__content conversation-seam__content--markdown"
          v-html="editorCsvTableHtml"
        />
        <CenterWorkbenchEditorFooter
          :is-ide-mode="isIdeMode"
          :show-minimap-toggle="!showAgentDiffReviewViewer"
          :editor-minimap-enabled="editorMinimapEnabled"
          :editor-cursor-line="editorCursorLine"
          :editor-cursor-column="editorCursorColumn"
          :editor-line-count="editorLineCount"
          :editor-eol="editorEol"
          :editor-language-label="editorLanguageLabel"
          :editor-access-status="editorAccessStatus"
          :terminal-chip="ideEditorStatusTerminalChip"
          :connector-chip="ideEditorStatusConnectorChip"
          :git-chip="ideEditorStatusGitChip"
          :search-chip="ideEditorStatusSearchChip"
          :team-chip="ideEditorStatusTeamChip"
          :problems-chip="ideEditorStatusProblemsChip"
          :agent-chip="ideEditorStatusAgentChip"
          @show-terminal="showTerminalPanel"
          @show-problems="onShowProblems"
          @open-connectors="onOpenWatchConnectors"
          @open-source-control="onOpenSourceControl"
          @open-search="onOpenSearch"
          @open-team="() => openIdeTeam(shell)"
          @show-agent="showAgentDock"
          @toggle-minimap="toggleEditorMinimap"
        />
      </section>
    </section>

    <OperatorStatusRadarPanel v-if="hideOperatorEditor" :terminal-visible="terminalPanelVisible" @toggle-terminal="toggleTerminalPanel" />
    <GalaxySpeechCaptions v-if="showGalaxySpeechCaptions" />
    <WorkbenchTerminalDock v-if="showTerminalDock" :hide-operator-editor="hideOperatorEditor" :log-lines="logLines" :output-lines="outputLines" :problem-items="problemItems" :terminal-height="terminalHeight" @hide="hideTerminalPanel" @start-resize="startTerminalResize" />
  </main>
</template>
