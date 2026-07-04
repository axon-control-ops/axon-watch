import { computed, ref } from 'vue';
import { defineStore } from 'pinia';

import {
  approveRun,
  completeRun,
  fetchInbox,
  fetchOperatorBriefing,
  fetchRuns,
  fetchRuntimeSummary,
  fetchWorkspaceFile,
  fetchWorkspaces,
  fetchWorkspaceFiles,
  markRunReviewReady,
  rejectRun,
  resumeRun,
  saveWorkspaceFile,
  stopRun,
} from '../api/control-plane';
import type {
  ApprovalRecord,
  InboxItem,
  OperatorBriefing,
  RunRecord,
  RuntimeSummary,
  SignalView,
  ThreadMessage,
  WorkspaceRecord,
} from '../contracts/canonical';
import {
  filePathFromDocumentId,
  workspaceFileDocumentId,
} from '../lib/workspace-file-language';
import {
  buildOpenedFileDocuments,
  pickPreferredWorkspaceFilePath,
  type FileContentLoadState,
} from '../lib/workspace-file-session';
import {
  buildWorkspaceDocuments,
  type WorkspaceDocumentDescriptor,
} from '../lib/workspace-documents';
import {
  selectPrimaryApprovalRun,
  selectPrimaryRun,
} from './shell-run-selection';
import { resolveKairoPresenceState, type KairoPresenceState } from '../lib/kairo-presence';

export type LayoutMode = 'operator' | 'ide';
export type RuntimeSummaryLoadState = 'idle' | 'loading' | 'loaded' | 'error';
export type InboxLoadState = 'idle' | 'loading' | 'loaded' | 'error';
export type RunsLoadState = 'idle' | 'loading' | 'loaded' | 'error';
export type WorkspacesLoadState = 'idle' | 'loading' | 'loaded' | 'error';
export type BriefingLoadState = 'idle' | 'loading' | 'loaded' | 'error';
export type WorkspaceFilesLoadState = 'idle' | 'loading' | 'loaded' | 'error';
export type RunMutationState =
  | 'idle'
  | 'stopping'
  | 'resuming'
  | 'approving'
  | 'rejecting'
  | 'reviewing'
  | 'completing';
type WorkbenchSurface = 'editor' | 'preview';

interface EditorTabDescriptor {
  id: string;
  title: string;
  surface: WorkbenchSurface;
  state: 'placeholder';
}

interface TerminalSessionDescriptor {
  id: string;
  title: string;
  state: 'placeholder';
}

interface DockContextDescriptor {
  id: string;
  title: string;
  state: 'placeholder';
}

const DEFAULT_EDITOR_TABS: EditorTabDescriptor[] = [
  { id: 'editor-shell', title: 'Editor Shell', surface: 'editor', state: 'placeholder' },
  { id: 'preview-shell', title: 'Preview Shell', surface: 'preview', state: 'placeholder' },
];

const DEFAULT_TERMINAL_SESSIONS: TerminalSessionDescriptor[] = [
  { id: 'terminal-primary', title: 'Terminal Shell', state: 'placeholder' },
];

const DEFAULT_DOCK_CONTEXT: DockContextDescriptor = {
  id: 'dock-thread',
  title: 'Dock Thread Shell',
  state: 'placeholder',
};

export const useShellStore = defineStore('shell', () => {
  const layoutMode = ref<LayoutMode>('operator');

  // Backend-owned state stays on shared canonical DTO seams.
  const workspaces = ref<WorkspaceRecord[]>([]);
  const currentWorkspace = ref<WorkspaceRecord | null>(null);
  const workspacesLoadState = ref<WorkspacesLoadState>('idle');
  const workspacesError = ref<string | null>(null);
  const runtimeSummary = ref<RuntimeSummary | null>(null);
  const runtimeSummaryLoadState = ref<RuntimeSummaryLoadState>('idle');
  const runtimeSummaryError = ref<string | null>(null);
  const activeRun = ref<RunRecord | null>(null);
  const runs = ref<RunRecord[]>([]);
  const runsLoadState = ref<RunsLoadState>('idle');
  const runsError = ref<string | null>(null);
  const runMutationState = ref<RunMutationState>('idle');
  const runMutationError = ref<string | null>(null);
  const approvals = ref<ApprovalRecord[]>([]);
  const inboxItems = ref<InboxItem[]>([]);
  const inboxLoadState = ref<InboxLoadState>('idle');
  const inboxError = ref<string | null>(null);
  const operatorBriefing = ref<OperatorBriefing | null>(null);
  const briefingLoadState = ref<BriefingLoadState>('idle');
  const briefingError = ref<string | null>(null);
  const signalViews = ref<SignalView[]>([]);
  const threadMessages = ref<ThreadMessage[]>([]);
  const workspaceFileEntries = ref<Array<{ path: string; size_bytes: number }>>([]);
  const workspaceFilesLoadState = ref<WorkspaceFilesLoadState>('idle');
  const workspaceFilesError = ref<string | null>(null);
  const fileContents = ref<Record<string, string>>({});
  const fileSavedContents = ref<Record<string, string>>({});
  const fileContentLoadStates = ref<Record<string, FileContentLoadState>>({});
  const openedFilePaths = ref<string[]>([]);
  const fileSaveState = ref<'idle' | 'saving'>('idle');
  const fileSaveError = ref<string | null>(null);

  // UI shell scaffolding is local and intentionally placeholder-only.
  const editorTabs = ref<EditorTabDescriptor[]>(DEFAULT_EDITOR_TABS);
  const activeEditorTabId = ref<string>(DEFAULT_EDITOR_TABS[0].id);
  const activeEditorDocumentId = ref<string>('file:README.md');
  const terminalSessions = ref<TerminalSessionDescriptor[]>(DEFAULT_TERMINAL_SESSIONS);
  const activeTerminalSessionId = ref<string>(DEFAULT_TERMINAL_SESSIONS[0].id);
  const dockContext = ref<DockContextDescriptor>(DEFAULT_DOCK_CONTEXT);

  const layoutModeLabel = computed(() =>
    layoutMode.value === 'operator' ? 'Operator mode' : 'IDE mode',
  );

  const workspaceStateLabel = computed(() =>
    currentWorkspace.value
      ? currentWorkspace.value.workspace_id
      : 'No workspace selected',
  );

  const runtimeStateLabel = computed(() => {
    if (runtimeSummaryLoadState.value === 'loading') {
      return 'Loading RuntimeSummary';
    }

    if (runtimeSummaryLoadState.value === 'error') {
      return 'RuntimeSummary unavailable';
    }

    if (!runtimeSummary.value) {
      return 'Awaiting RuntimeSummary';
    }

    const identity = runtimeSummary.value.runtime_identity;
    const watchConnected = runtimeSummary.value.watch.connected ? 'watch connected' : 'watch disconnected';
    const activeRunCount = runtimeSummary.value.active_runs.length;

    return `${identity.provider_name} / ${identity.model_name} · ${activeRunCount} active run(s) · ${watchConnected}`;
  });

  const runStateLabel = computed(() => {
    if (runsLoadState.value === 'loading') {
      return 'Loading RunRecord';
    }

    if (runsLoadState.value === 'error') {
      return 'RunRecord unavailable';
    }

    if (!activeRun.value) {
      return 'No active run';
    }

    const run = activeRun.value;
    return `${run.run_id} · ${run.phase} · ${run.summary}`;
  });

  const primaryActiveRun = computed(() => activeRun.value);
  const primaryApprovalRun = computed(() => selectPrimaryApprovalRun(runs.value));
  const workspaceRuns = computed(() =>
    currentWorkspace.value
      ? runs.value.filter((run) => run.workspace_id === currentWorkspace.value?.workspace_id)
      : runs.value,
  );
  const workspacePrimarySignal = computed(() =>
    currentWorkspace.value
      ? inboxItems.value.find((item) => item.workspace_id === currentWorkspace.value?.workspace_id) ??
        primaryInboxItem.value
      : primaryInboxItem.value,
  );
  const dtoDocuments = computed<WorkspaceDocumentDescriptor[]>(() =>
    buildWorkspaceDocuments({
      workspace: currentWorkspace.value,
      runs: workspaceRuns.value,
      runtimeSummary: runtimeSummary.value,
      primaryInboxItem: workspacePrimarySignal.value,
    }),
  );
  const fileDocuments = computed<WorkspaceDocumentDescriptor[]>(() =>
    buildOpenedFileDocuments(
      workspaceFileEntries.value,
      openedFilePaths.value,
      fileContents.value,
      fileSavedContents.value,
      fileContentLoadStates.value,
    ),
  );
  const editorDocuments = computed<WorkspaceDocumentDescriptor[]>(() => [
    ...fileDocuments.value,
    ...dtoDocuments.value,
  ]);
  const activeEditorDocument = computed(
    () =>
      editorDocuments.value.find((document) => document.id === activeEditorDocumentId.value) ??
      editorDocuments.value[0] ??
      null,
  );
  const runMutationPending = computed(() => runMutationState.value !== 'idle');
  const canStopPrimaryRun = computed(
    () => Boolean(activeRun.value?.can_stop) && !runMutationPending.value,
  );
  const canResumePrimaryRun = computed(
    () => Boolean(activeRun.value?.can_resume) && !runMutationPending.value,
  );
  const canMarkPrimaryRunReviewReady = computed(
    () => activeRun.value?.phase === 'executing' && !runMutationPending.value,
  );
  const canCompletePrimaryRun = computed(
    () => activeRun.value?.phase === 'review_ready' && !runMutationPending.value,
  );

  const inboxStateLabel = computed(() => {
    if (inboxLoadState.value === 'loading') {
      return 'Loading inbox signal';
    }

    if (inboxLoadState.value === 'error') {
      return 'Inbox signal unavailable';
    }

    const primary = inboxItems.value[0];
    if (!primary) {
      return 'No open signals';
    }

    return `${primary.title} · ${primary.severity}`;
  });

  const primaryInboxItem = computed(() => inboxItems.value[0] ?? null);

  const canApprovePrimaryRun = computed(
    () => Boolean(primaryApprovalRun.value?.can_approve) && !runMutationPending.value,
  );
  const canRejectPrimaryRun = computed(
    () => primaryApprovalRun.value?.phase === 'awaiting_approval' && !runMutationPending.value,
  );

  const threadStateLabel = computed(() =>
    threadMessages.value.length > 0 ? 'Conversation active' : 'No active conversation',
  );

  const kairoPresenceState = computed<KairoPresenceState>(() => {
    const summary = runtimeSummary.value;
    return resolveKairoPresenceState({
      pendingApprovals:
        summary?.approvals.pending_count ?? operatorBriefing.value?.pending_approvals.count ?? 0,
      criticalSignals: summary?.signals.critical_count ?? 0,
      highSignals: summary?.signals.high_count ?? 0,
      watchConnected: Boolean(summary?.watch.connected),
      runtimeLoaded: runtimeSummaryLoadState.value === 'loaded' && Boolean(summary),
    });
  });

  const showDevSeams = computed(() => import.meta.env.VITE_DEV_SEAMS === '1');

  const statusBarItems = computed(() => {
    const items: string[] = [layoutModeLabel.value];
    if (currentWorkspace.value?.workspace_id) {
      items.push(currentWorkspace.value.workspace_id);
    }
    if (runtimeSummary.value) {
      items.push(runtimeSummary.value.watch.connected ? 'watch connected' : 'watch offline');
    }
    if (activeRun.value) {
      items.push(`${activeRun.value.run_id} · ${activeRun.value.phase}`);
    }
    const pendingApprovals =
      runtimeSummary.value?.approvals.pending_count ??
      operatorBriefing.value?.pending_approvals.count ??
      0;
    if (pendingApprovals > 0) {
      items.push(`approvals: ${pendingApprovals}`);
    }
    const openSignals = runtimeSummary.value?.signals.open_count ?? 0;
    if (openSignals > 0) {
      items.push(`signals: ${openSignals}`);
    }
    if (runtimeSummary.value?.degraded.active) {
      items.push(runtimeSummary.value.degraded.reasons[0] ?? 'degraded');
    }
    return items;
  });

  function syncCurrentWorkspace(preferredWorkspaceId?: string | null): void {
    if (workspaces.value.length === 0) {
      currentWorkspace.value = null;
      return;
    }

    const targetWorkspaceId =
      preferredWorkspaceId ??
      currentWorkspace.value?.workspace_id ??
      activeRun.value?.workspace_id ??
      workspaces.value[0]?.workspace_id;
    currentWorkspace.value =
      workspaces.value.find((workspace) => workspace.workspace_id === targetWorkspaceId) ??
      workspaces.value[0] ??
      null;
  }

  function setLayoutMode(mode: LayoutMode): void {
    layoutMode.value = mode;
  }

  const activeWorkspaceFilePath = computed(() => {
    const path = filePathFromDocumentId(activeEditorDocumentId.value);
    return path && openedFilePaths.value.includes(path) ? path : null;
  });

  function setActiveEditorTab(id: string): void {
    activeEditorTabId.value = id;
  }

  function setActiveEditorDocument(id: string): void {
    activeEditorDocumentId.value = id;
    const path = filePathFromDocumentId(id);
    if (path) {
      void openWorkspaceFile(path);
    }
  }

  async function ensureWorkspaceFileLoaded(path: string): Promise<void> {
    const workspaceId = currentWorkspace.value?.workspace_id;
    if (!workspaceId || fileContentLoadStates.value[path] === 'loaded') {
      return;
    }

    if (fileContentLoadStates.value[path] === 'loading') {
      return;
    }

    fileContentLoadStates.value = {
      ...fileContentLoadStates.value,
      [path]: 'loading',
    };

    try {
      const payload = await fetchWorkspaceFile(workspaceId, path);
      fileContents.value = {
        ...fileContents.value,
        [path]: payload.content,
      };
      if (fileSavedContents.value[path] === undefined) {
        fileSavedContents.value = {
          ...fileSavedContents.value,
          [path]: payload.content,
        };
      }
      fileContentLoadStates.value = {
        ...fileContentLoadStates.value,
        [path]: 'loaded',
      };
    } catch (error) {
      fileContentLoadStates.value = {
        ...fileContentLoadStates.value,
        [path]: 'error',
      };
      workspaceFilesError.value =
        error instanceof Error ? error.message : 'workspace file request failed';
    }
  }

  async function openWorkspaceFile(path: string): Promise<void> {
    if (!openedFilePaths.value.includes(path)) {
      openedFilePaths.value = [...openedFilePaths.value, path];
    }

    activeEditorDocumentId.value = workspaceFileDocumentId(path);
    await ensureWorkspaceFileLoaded(path);
  }

  function setCurrentWorkspace(workspaceId: string): void {
    syncCurrentWorkspace(workspaceId);
    void loadWorkspaceFiles();
  }

  async function loadWorkspaceFiles(): Promise<void> {
    const workspaceId = currentWorkspace.value?.workspace_id;
    if (!workspaceId) {
      workspaceFileEntries.value = [];
      openedFilePaths.value = [];
      fileContents.value = {};
      fileSavedContents.value = {};
      fileContentLoadStates.value = {};
      workspaceFilesLoadState.value = 'idle';
      return;
    }

    workspaceFilesLoadState.value = 'loading';
    workspaceFilesError.value = null;

    try {
      const snapshot = await fetchWorkspaceFiles(workspaceId);
      workspaceFileEntries.value = snapshot.items;
      fileContents.value = {};
      fileSavedContents.value = {};
      fileContentLoadStates.value = {};
      workspaceFilesLoadState.value = 'loaded';

      const preferredPath = pickPreferredWorkspaceFilePath(snapshot.items);
      openedFilePaths.value = preferredPath ? [preferredPath] : [];
      if (preferredPath) {
        activeEditorDocumentId.value = workspaceFileDocumentId(preferredPath);
        await ensureWorkspaceFileLoaded(preferredPath);
      }
    } catch (error) {
      workspaceFilesLoadState.value = 'error';
      workspaceFilesError.value =
        error instanceof Error ? error.message : 'workspace files request failed';
    }
  }

  function updateActiveFileContent(value: string): void {
    const document = activeEditorDocument.value;
    if (document?.source !== 'file' || !document.filePath) {
      return;
    }

    fileContents.value = {
      ...fileContents.value,
      [document.filePath]: value,
    };
  }

  async function saveActiveFileDocument(): Promise<void> {
    const document = activeEditorDocument.value;
    const workspaceId = currentWorkspace.value?.workspace_id;
    if (document?.source !== 'file' || !document.filePath || !workspaceId) {
      return;
    }

    fileSaveState.value = 'saving';
    fileSaveError.value = null;

    try {
      const content = fileContents.value[document.filePath] ?? '';
      await saveWorkspaceFile(workspaceId, document.filePath, content);
      fileSavedContents.value = {
        ...fileSavedContents.value,
        [document.filePath]: content,
      };
    } catch (error) {
      fileSaveError.value = error instanceof Error ? error.message : 'workspace file save failed';
    } finally {
      fileSaveState.value = 'idle';
    }
  }

  async function loadWorkspaces(): Promise<void> {
    workspacesLoadState.value = 'loading';
    workspacesError.value = null;

    try {
      const snapshot = await fetchWorkspaces();
      workspaces.value = snapshot.items;
      syncCurrentWorkspace();
      workspacesLoadState.value = 'loaded';
    } catch (error) {
      workspacesLoadState.value = 'error';
      workspacesError.value = error instanceof Error ? error.message : 'workspaces request failed';
    }
  }

  async function loadRuntimeSummary(): Promise<void> {
    runtimeSummaryLoadState.value = 'loading';
    runtimeSummaryError.value = null;

    try {
      const summary = await fetchRuntimeSummary();
      runtimeSummary.value = summary;
      runtimeSummaryLoadState.value = 'loaded';
    } catch (error) {
      runtimeSummaryLoadState.value = 'error';
      runtimeSummaryError.value =
        error instanceof Error ? error.message : 'runtime summary request failed';
    }
  }

  async function loadInbox(): Promise<void> {
    inboxLoadState.value = 'loading';
    inboxError.value = null;

    try {
      const inbox = await fetchInbox();
      inboxItems.value = inbox.items;
      signalViews.value = inbox.items;
      inboxLoadState.value = 'loaded';
    } catch (error) {
      inboxLoadState.value = 'error';
      inboxError.value = error instanceof Error ? error.message : 'inbox request failed';
    }
  }

  async function loadOperatorBriefing(): Promise<void> {
    briefingLoadState.value = 'loading';
    briefingError.value = null;

    try {
      operatorBriefing.value = await fetchOperatorBriefing();
      approvals.value = operatorBriefing.value.pending_approvals.items;
      briefingLoadState.value = 'loaded';
    } catch (error) {
      briefingLoadState.value = 'error';
      briefingError.value =
        error instanceof Error ? error.message : 'operator briefing request failed';
    }
  }

  async function loadRuns(): Promise<void> {
    runsLoadState.value = 'loading';
    runsError.value = null;

    try {
      const snapshot = await fetchRuns();
      runs.value = snapshot.items;
      activeRun.value = selectPrimaryRun(snapshot.items);
      syncCurrentWorkspace(activeRun.value?.workspace_id);
      runsLoadState.value = 'loaded';
    } catch (error) {
      runsLoadState.value = 'error';
      runsError.value = error instanceof Error ? error.message : 'runs request failed';
    }
  }

  async function refreshRunSurfaces(): Promise<void> {
    await Promise.all([loadRuns(), loadRuntimeSummary(), loadInbox(), loadOperatorBriefing()]);
  }

  async function stopPrimaryRun(): Promise<void> {
    const run = activeRun.value;
    if (!run?.can_stop || runMutationPending.value) {
      return;
    }

    runMutationState.value = 'stopping';
    runMutationError.value = null;

    try {
      await stopRun(run.run_id);
      await refreshRunSurfaces();
    } catch (error) {
      runMutationError.value = error instanceof Error ? error.message : 'stop run request failed';
    } finally {
      runMutationState.value = 'idle';
    }
  }

  async function resumePrimaryRun(): Promise<void> {
    const run = activeRun.value;
    if (!run?.can_resume || runMutationPending.value) {
      return;
    }

    runMutationState.value = 'resuming';
    runMutationError.value = null;

    try {
      await resumeRun(run.run_id);
      await refreshRunSurfaces();
    } catch (error) {
      runMutationError.value = error instanceof Error ? error.message : 'resume run request failed';
    } finally {
      runMutationState.value = 'idle';
    }
  }

  async function markPrimaryRunReviewReady(): Promise<void> {
    const run = activeRun.value;
    if (run?.phase !== 'executing' || runMutationPending.value) {
      return;
    }

    runMutationState.value = 'reviewing';
    runMutationError.value = null;

    try {
      await markRunReviewReady(run.run_id);
      await refreshRunSurfaces();
    } catch (error) {
      runMutationError.value =
        error instanceof Error ? error.message : 'review-ready request failed';
    } finally {
      runMutationState.value = 'idle';
    }
  }

  async function completePrimaryRun(): Promise<void> {
    const run = activeRun.value;
    if (run?.phase !== 'review_ready' || runMutationPending.value) {
      return;
    }

    runMutationState.value = 'completing';
    runMutationError.value = null;

    try {
      await completeRun(run.run_id);
      await refreshRunSurfaces();
    } catch (error) {
      runMutationError.value =
        error instanceof Error ? error.message : 'complete run request failed';
    } finally {
      runMutationState.value = 'idle';
    }
  }

  async function approvePrimaryRun(): Promise<void> {
    const run = primaryApprovalRun.value;
    if (!run?.can_approve || runMutationPending.value) {
      return;
    }

    runMutationState.value = 'approving';
    runMutationError.value = null;

    try {
      await approveRun(run.run_id);
      await refreshRunSurfaces();
    } catch (error) {
      runMutationError.value = error instanceof Error ? error.message : 'approve run request failed';
    } finally {
      runMutationState.value = 'idle';
    }
  }

  async function rejectPrimaryRun(): Promise<void> {
    const run = primaryApprovalRun.value;
    if (run?.phase !== 'awaiting_approval' || runMutationPending.value) {
      return;
    }

    runMutationState.value = 'rejecting';
    runMutationError.value = null;

    try {
      await rejectRun(run.run_id);
      await refreshRunSurfaces();
    } catch (error) {
      runMutationError.value = error instanceof Error ? error.message : 'reject run request failed';
    } finally {
      runMutationState.value = 'idle';
    }
  }

  async function loadBootstrapData(): Promise<void> {
    await Promise.all([
      loadRuntimeSummary(),
      loadInbox(),
      loadWorkspaces(),
      loadRuns(),
      loadOperatorBriefing(),
    ]);
    await loadWorkspaceFiles();
  }

  return {
    activeEditorTabId,
    activeEditorDocument,
    activeEditorDocumentId,
    activeRun,
    activeTerminalSessionId,
    activeWorkspaceFilePath,
    approvePrimaryRun,
    approvals,
    briefingError,
    briefingLoadState,
    canApprovePrimaryRun,
    canCompletePrimaryRun,
    canMarkPrimaryRunReviewReady,
    canRejectPrimaryRun,
    currentWorkspace,
    editorDocuments,
    canResumePrimaryRun,
    canStopPrimaryRun,
    dockContext,
    editorTabs,
    inboxError,
    inboxItems,
    inboxLoadState,
    inboxStateLabel,
    kairoPresenceState,
    layoutMode,
    layoutModeLabel,
    completePrimaryRun,
    loadBootstrapData,
    loadInbox,
    loadOperatorBriefing,
    loadRuns,
    loadRuntimeSummary,
    loadWorkspaces,
    markPrimaryRunReviewReady,
    operatorBriefing,
    primaryActiveRun,
    primaryApprovalRun,
    primaryInboxItem,
    rejectPrimaryRun,
    resumePrimaryRun,
    runs,
    runsError,
    runsLoadState,
    runMutationError,
    runMutationPending,
    runMutationState,
    runStateLabel,
    runtimeStateLabel,
    runtimeSummary,
    runtimeSummaryError,
    runtimeSummaryLoadState,
    showDevSeams,
    statusBarItems,
    setActiveEditorTab,
    setActiveEditorDocument,
    setCurrentWorkspace,
    setLayoutMode,
    signalViews,
    stopPrimaryRun,
    terminalSessions,
    threadMessages,
    threadStateLabel,
    fileSaveError,
    fileSaveState,
    loadWorkspaceFiles,
    openWorkspaceFile,
    saveActiveFileDocument,
    updateActiveFileContent,
    workspaceFileEntries,
    workspaceFilesError,
    workspaceFilesLoadState,
    workspacesError,
    workspacesLoadState,
    workspacePrimarySignal,
    workspaceStateLabel,
    workspaces,
  };
});
