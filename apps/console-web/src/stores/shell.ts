import { computed, ref } from 'vue';
import { defineStore } from 'pinia';

import {
  approveRun,
  acknowledgeInboxSignals,
  completeRun,
  fetchConnectors,
  fetchInbox,
  fetchOperatorBriefing,
  fetchOperatorPresenceSettings,
  fetchRunHistory,
  fetchRuns,
  fetchRuntimeSummary,
  fetchThreadHistory,
  fetchWorkspaceChatThread,
  hasWorkspaceChatThread,
  fetchWorkspaceFile,
  fetchWorkspaces,
  fetchWorkspaceFiles,
  markRunReviewReady,
  postChatMessage,
  postWatchCommand,
  rejectRun,
  renameWorkspaceFile,
  resumeRun,
  saveWorkspaceFile,
  saveOperatorPresenceSettings,
  stopRun,
} from '../api/control-plane';
import type { ConnectorProbeRecord } from '../api/control-plane';
import type {
  ApprovalRecord,
  InboxItem,
  OperatorBriefing,
  OperatorPresenceSettings,
  RunRecord,
  RuntimeSummary,
  SignalView,
  WorkspaceRecord,
} from '../contracts/canonical';
import { deliverSpokenOperatorAlert } from '../lib/spoken-alert-delivery';
import { isBootstrapSummarySignal } from '../lib/operator-signal-hints';
import {
  readViewportWidth,
  shouldRequestViewportCompactBriefing,
  shouldUseMobileCompactLayout,
} from '../lib/viewport-compact';
import {
  defaultOperatorPresenceSettings,
  normalizeOperatorPresenceSettings,
  persistOperatorPresenceSettings,
  readPersistedOperatorPresenceSettings,
} from '../lib/operator-presence-settings';
import {
  buildRunHistoryRows,
  type RunHistorySnapshot,
} from '../lib/run-history-view';
import { formatRunIdentityLabel } from '../lib/run-display';
import { isOperatorCompletablePhase } from '../lib/run-lifecycle-ui';
import {
  appendOperatorCommand,
  canSubmitOperatorCommand as canSubmitOperatorCommandDraft,
  commandSeamHint as buildCommandSeamHint,
  conversationEmptyStateLabel,
  mapChatMessageRecord,
  mergeThreadMessages,
  type OperatorThreadEntry,
} from '../lib/operator-thread';
import {
  filePathFromDocumentId,
  workspaceFileDocumentId,
} from '../lib/workspace-file-language';
import {
  buildOpenedFileDocuments,
  isSafeWorkspaceFilePath,
  normalizeWorkspaceFilePath,
  pickPreferredWorkspaceFilePath,
  remapWorkspaceFilePaths,
  remapWorkspaceFileRecord,
  type FileContentLoadState,
} from '../lib/workspace-file-session';
import {
  buildWorkspaceDocuments,
  type WorkspaceDocumentDescriptor,
} from '../lib/workspace-documents';
import {
  selectPrimaryApprovalRun,
  selectPrimaryRun,
  selectWorkspacePrimaryRun,
} from './shell-run-selection';
import { resolveKairoPresenceState, type KairoPresenceState } from '../lib/kairo-presence';
import {
  buildDockSeamLayout,
  type DockSeamId,
} from '../lib/dock-seam-layout';
import {
  resolveDefaultDockHeroMode,
  type DockHeroMode,
} from '../lib/dock-hero-mode';
import {
  leftSidebarAttentionBadgeCount as computeLeftSidebarAttentionBadgeCount,
  persistLeftSidebarMode,
  readStoredLeftSidebarMode,
  resolveDefaultLeftSidebarMode,
  type LeftSidebarMode,
} from '../lib/left-sidebar-mode';
import {
  briefingAttentionStatusLabel,
  resolveKairoBriefingAttention,
  shouldShowBriefingAttentionInCommandMode,
} from '../lib/kairo-briefing-attention';
import {
  buildStatusBarSegments,
  buildTopbarChips,
} from '../lib/runtime-strip';
import {
  persistOperatorWorkspaceId,
  readStoredOperatorWorkspaceId,
} from '../lib/operator-workspace-selection';
import {
  defaultOperatorWorkspaceId,
  mergeOperatorWorkspaceCatalog,
  workspaceCatalogMode,
} from '../lib/operator-workspace-catalog';
import {
  buildBriefingSummaryLine,
  buildStatusBarZones,
  buildTopbarBreadcrumb,
  buildTopbarMetaPills,
  buildWorkspaceStatusCardRows,
  resolveOperatorWorkspaceId,
} from '../lib/mockup-shell-view';
import {
  type IdeActivityView,
  persistAgentDockCollapsed,
  persistIdeExplorerCollapsed,
  persistLayoutMode,
  readStoredAgentDockCollapsed,
  readStoredIdeExplorerCollapsed,
  readStoredLayoutMode,
} from '../lib/ide-layout-prefs';
import { persistWorkbenchTerminalPanelVisible } from '../lib/workbench-terminal-split';

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
  { id: 'editor-shell', title: 'Editor', surface: 'editor', state: 'placeholder' },
  { id: 'preview-shell', title: 'Preview', surface: 'preview', state: 'placeholder' },
];

const DEFAULT_TERMINAL_SESSIONS: TerminalSessionDescriptor[] = [
  { id: 'terminal-primary', title: 'Terminal', state: 'placeholder' },
];

const DEFAULT_DOCK_CONTEXT: DockContextDescriptor = {
  id: 'dock-thread',
  title: 'Dock Thread Shell',
  state: 'placeholder',
};

export const useShellStore = defineStore('shell', () => {
  const layoutMode = ref<LayoutMode>(readStoredLayoutMode() ?? 'operator');

  // Backend-owned state stays on shared canonical DTO seams.
  const workspaces = ref<WorkspaceRecord[]>([]);
  const currentWorkspace = ref<WorkspaceRecord | null>(null);
  const operatorPinnedWorkspaceId = ref<string | null>(readStoredOperatorWorkspaceId());
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
  const signalClearState = ref<'idle' | 'clearing'>('idle');
  const signalClearError = ref<string | null>(null);
  const runHistorySnapshot = ref<RunHistorySnapshot | null>(null);
  const runHistoryLoadState = ref<'idle' | 'loading' | 'loaded' | 'error'>('idle');
  const approvals = ref<ApprovalRecord[]>([]);
  const inboxItems = ref<InboxItem[]>([]);
  const inboxLoadState = ref<InboxLoadState>('idle');
  const inboxError = ref<string | null>(null);
  const connectorsItems = ref<ConnectorProbeRecord[]>([]);
  const connectorsSummary = ref<{
    configured: number;
    ok: number;
    degraded: number;
    unavailable: number;
    required_unavailable: number;
  } | null>(null);
  const connectorsLoadState = ref<'idle' | 'loading' | 'loaded' | 'error'>('idle');
  const connectorsError = ref<string | null>(null);
  const connectorMutationPending = ref(false);
  const operatorBriefing = ref<OperatorBriefing | null>(null);
  const operatorPresenceSettings = ref<OperatorPresenceSettings>(
    readPersistedOperatorPresenceSettings() ?? defaultOperatorPresenceSettings(),
  );
  const operatorPresenceSettingsOpen = ref(false);
  const operatorPresenceSettingsSaving = ref(false);
  const viewportWidth = ref(readViewportWidth());
  let lastViewportCompactRequested: boolean | null = null;
  let viewportCompactListenerBound = false;
  const briefingLoadState = ref<BriefingLoadState>('idle');
  const briefingError = ref<string | null>(null);
  const signalViews = ref<SignalView[]>([]);
  const threadMessages = ref<OperatorThreadEntry[]>([]);
  const activeThreadId = ref<string | null>(null);
  const workspaceThreadIds = ref<Record<string, string>>({});
  const operatorCommandDraft = ref('');
  const commandMutationState = ref<'idle' | 'submitting' | 'error'>('idle');
  const commandMutationError = ref<string | null>(null);
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
  const expandedDockSeams = ref<Set<DockSeamId>>(new Set());
  const briefingSeamEmphasized = ref(false);
  const missionControlEmphasized = ref(false);
  const signalsSeamEmphasized = ref(false);
  const highlightedSignalId = ref<string | null>(null);
  const dockHeroMode = ref<DockHeroMode>('command');
  const dockHeroModeTouched = ref(false);
  const commandFocusToken = ref(0);
  const leftSidebarMode = ref<LeftSidebarMode>(readStoredLeftSidebarMode() ?? 'workspaces');
  const leftSidebarModeTouched = ref(Boolean(readStoredLeftSidebarMode()));
  const ideActivityView = ref<IdeActivityView>('explorer');
  const ideExplorerCollapsed = ref(readStoredIdeExplorerCollapsed());
  const agentDockCollapsed = ref(readStoredAgentDockCollapsed());
  const ideTerminalRevealToken = ref(0);
  const ideTerminalToggleToken = ref(0);


  const layoutModeLabel = computed(() =>
    layoutMode.value === 'operator' ? 'Operator mode' : 'IDE mode',
  );

  const workspaceTrailLabel = computed(() => {
    const workspace = currentWorkspace.value?.workspace_id ?? 'No workspace selected';
    const identity = runtimeSummary.value?.runtime_identity;
    if (!identity) {
      return workspace;
    }
    return `${workspace} / ${identity.provider_name}`;
  });

  const workspaceStateLabel = computed(() => {
    if (!currentWorkspace.value) {
      return 'No workspace selected';
    }
    return currentWorkspace.value.display_name?.trim() || currentWorkspace.value.workspace_id;
  });

  const usesProductionWorkspaceCatalog = computed(
    () => workspaceCatalogMode(workspaces.value) === 'production',
  );

  const topbarChips = computed(() =>
    buildTopbarChips({
      runtimeSummary: runtimeSummary.value,
      runtimeSummaryLoadState: runtimeSummaryLoadState.value,
      primaryActiveRun: activeRun.value,
    }),
  );

  const topbarMetaPills = computed(() => buildTopbarMetaPills(runtimeSummary.value));
  const topbarBreadcrumb = computed(() =>
    buildTopbarBreadcrumb(runtimeSummary.value, currentWorkspace.value),
  );
  const statusBarZones = computed(() =>
    buildStatusBarZones({
      runtimeSummary: runtimeSummary.value,
      runtimeSummaryLoadState: runtimeSummaryLoadState.value,
      primaryActiveRun: primaryActiveRun.value,
      workspaceId: currentWorkspace.value?.workspace_id ?? null,
    }),
  );

  const workspaceStatusCardRows = computed(() =>
    buildWorkspaceStatusCardRows({
      runtimeSummary: runtimeSummary.value,
      runtimeSummaryLoadState: runtimeSummaryLoadState.value,
    }),
  );

  const briefingSummaryLine = computed(() =>
    buildBriefingSummaryLine(
      operatorBriefing.value,
      runtimeSummary.value,
      currentWorkspace.value?.workspace_id ?? null,
    ),
  );

  const runtimeStateLabel = computed(() => topbarChips.value.map((chip) => chip.label).join(' · '));

  const workspaceRuns = computed(() =>
    currentWorkspace.value
      ? runs.value.filter((run) => run.workspace_id === currentWorkspace.value?.workspace_id)
      : runs.value,
  );
  const primaryActiveRun = computed(() => selectWorkspacePrimaryRun(workspaceRuns.value));
  const runStateLabel = computed(() => {
    if (runsLoadState.value === 'loading') {
      return 'Loading active run…';
    }

    if (runsLoadState.value === 'error') {
      return 'Active run unavailable';
    }

    if (!primaryActiveRun.value) {
      return 'No active run';
    }

    const run = primaryActiveRun.value;
    return formatRunIdentityLabel(run);
  });
  const runHistoryRows = computed(() => buildRunHistoryRows(runHistorySnapshot.value));
  const primaryApprovalRun = computed(() => selectPrimaryApprovalRun(runs.value));
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
  const activeEditorDocument = computed(() => {
    const matched = editorDocuments.value.find(
      (document) => document.id === activeEditorDocumentId.value,
    );
    if (matched) {
      return matched;
    }

    if (fileDocuments.value.length > 0) {
      return fileDocuments.value[0];
    }

    return editorDocuments.value[0] ?? null;
  });
  const runMutationPending = computed(() => runMutationState.value !== 'idle');
  const canStopPrimaryRun = computed(
    () => Boolean(primaryActiveRun.value?.can_stop) && !runMutationPending.value,
  );
  const canResumePrimaryRun = computed(
    () => Boolean(primaryActiveRun.value?.can_resume) && !runMutationPending.value,
  );
  const canMarkPrimaryRunReviewReady = computed(
    () => primaryActiveRun.value?.phase === 'executing' && !runMutationPending.value,
  );
  const canCompletePrimaryRun = computed(
    () =>
      isOperatorCompletablePhase(primaryActiveRun.value?.phase) && !runMutationPending.value,
  );

  const inboxStateLabel = computed(() => {
    if (inboxLoadState.value === 'loading') {
      return 'Loading signals…';
    }

    if (inboxLoadState.value === 'error') {
      return 'Signals unavailable';
    }

    const primary = inboxItems.value[0];
    if (!primary) {
      return 'No open signals';
    }

    return `${primary.title} · ${primary.severity}`;
  });

  const approvalsSummaryLabel = computed(() => {
    const pending =
      runtimeSummary.value?.approvals.pending_count ??
      operatorBriefing.value?.pending_approvals.count ??
      0;
    if (pending === 0) {
      return 'No pending approvals';
    }
    return `${pending} pending approval${pending === 1 ? '' : 's'}`;
  });

  const primaryInboxItem = computed(() => inboxItems.value[0] ?? null);

  const canApprovePrimaryRun = computed(
    () => Boolean(primaryApprovalRun.value?.can_approve) && !runMutationPending.value,
  );
  const canRejectPrimaryRun = computed(
    () => primaryApprovalRun.value?.phase === 'awaiting_approval' && !runMutationPending.value,
  );

  const threadStateLabel = computed(() =>
    conversationEmptyStateLabel(threadMessages.value.length),
  );

  const canSubmitOperatorCommand = computed(
    () =>
      commandMutationState.value !== 'submitting' &&
      canSubmitOperatorCommandDraft(
        operatorCommandDraft.value,
        currentWorkspace.value?.workspace_id ?? null,
      ),
  );

  const commandSeamHint = computed(() =>
    buildCommandSeamHint(currentWorkspace.value?.workspace_id ?? null),
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

  const kairoBriefingAttention = computed(() =>
    resolveKairoBriefingAttention({
      pendingApprovals: pendingApprovalsCount.value,
      criticalSignals: runtimeSummary.value?.signals.critical_count ?? 0,
      highSignals: runtimeSummary.value?.signals.high_count ?? 0,
      degraded:
        operatorBriefing.value?.degraded.active ??
        runtimeSummary.value?.degraded.active ??
        false,
      briefingLoaded: briefingLoadState.value === 'loaded',
    }),
  );

  const showKairoBriefingAttention = computed(() =>
    shouldShowBriefingAttentionInCommandMode(dockHeroMode.value, kairoBriefingAttention.value),
  );

  const kairoBriefingAttentionLabel = computed(() =>
    briefingAttentionStatusLabel(kairoBriefingAttention.value),
  );

  const showDevSeams = computed(() => import.meta.env.VITE_DEV_SEAMS === '1');

  const mobileCompactLayout = computed(() =>
    shouldUseMobileCompactLayout(
      viewportWidth.value,
      operatorBriefing.value?.operator_presence ?? null,
      operatorPresenceSettings.value,
    ),
  );

  const pendingApprovalsCount = computed(() => {
    const fromSummary = runtimeSummary.value?.approvals.pending_count ?? 0;
    const fromBriefing = operatorBriefing.value?.pending_approvals.count ?? 0;
    return Math.max(fromSummary, fromBriefing);
  });

  const leftSidebarAttentionBadgeCount = computed(() =>
    computeLeftSidebarAttentionBadgeCount({
      pendingApprovals: pendingApprovalsCount.value,
      briefing: operatorBriefing.value,
    }),
  );

  const statusBarSegments = computed(() =>
    buildStatusBarSegments({
      layoutModeLabel: layoutModeLabel.value,
      workspaceId: currentWorkspace.value?.workspace_id ?? null,
      runtimeSummary: runtimeSummary.value,
      pendingApprovals: pendingApprovalsCount.value,
    }),
  );

  const statusBarItems = computed(() => statusBarSegments.value.map((segment) => segment.label));

  const dockSeamLayout = computed(() =>
    buildDockSeamLayout({
      layoutMode: layoutMode.value,
      briefing: operatorBriefing.value,
      approvalsSummary: approvalsSummaryLabel.value,
      signalsSummary: inboxStateLabel.value,
      runSummary: runStateLabel.value,
      threadSummary: threadStateLabel.value,
      expandedSeams: expandedDockSeams.value,
    }),
  );

  function dockSeamState(id: DockSeamId) {
    return dockSeamLayout.value.find((seam) => seam.id === id) ?? null;
  }

  function toggleDockSeam(id: DockSeamId): void {
    const next = new Set(expandedDockSeams.value);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    expandedDockSeams.value = next;
  }

  function resetThreadContext(): void {
    threadMessages.value = [];
    activeThreadId.value = null;
    operatorCommandDraft.value = '';
    commandMutationState.value = 'idle';
    commandMutationError.value = null;
  }

  async function loadWorkspaceThread(workspaceId: string): Promise<void> {
    try {
      let threadId = workspaceThreadIds.value[workspaceId] ?? null;
      if (!threadId) {
        const workspaceThread = await fetchWorkspaceChatThread(workspaceId);
        if (!hasWorkspaceChatThread(workspaceThread)) {
          resetThreadContext();
          return;
        }

        threadId = workspaceThread.thread_id;
        workspaceThreadIds.value = {
          ...workspaceThreadIds.value,
          [workspaceId]: threadId,
        };
      }

      const history = await fetchThreadHistory(threadId);
      activeThreadId.value = history.thread_id;
      threadMessages.value = history.items.map((item) => mapChatMessageRecord(item));
      commandMutationState.value = 'idle';
      commandMutationError.value = null;
    } catch (error) {
      const nextThreadIds = { ...workspaceThreadIds.value };
      delete nextThreadIds[workspaceId];
      workspaceThreadIds.value = nextThreadIds;
      resetThreadContext();
      commandMutationState.value = 'error';
      commandMutationError.value =
        error instanceof Error ? error.message : 'Failed to load conversation history';
    }
  }

  async function submitOperatorCommand(): Promise<void> {
    const workspaceId = currentWorkspace.value?.workspace_id ?? null;
    const content = operatorCommandDraft.value.trim();
    if (!canSubmitOperatorCommand.value || !workspaceId || !content) {
      return;
    }

    commandMutationState.value = 'submitting';
    commandMutationError.value = null;

    try {
      const response = await postChatMessage({
        workspace_id: workspaceId,
        content,
        thread_id: activeThreadId.value,
        run_id: primaryActiveRun.value?.run_id ?? null,
      });
      activeThreadId.value = response.thread_id;
      workspaceThreadIds.value = {
        ...workspaceThreadIds.value,
        [workspaceId]: response.thread_id,
      };
      threadMessages.value = mergeThreadMessages(
        threadMessages.value,
        response.messages.map((message) => mapChatMessageRecord(message)),
      );
      operatorCommandDraft.value = '';
      commandMutationState.value = 'idle';
      await refreshRunSurfaces();

      const next = new Set(expandedDockSeams.value);
      next.add('thread');
      expandedDockSeams.value = next;
    } catch (error) {
      commandMutationState.value = 'error';
      commandMutationError.value =
        error instanceof Error ? error.message : 'Failed to submit operator command';
    }
  }

  async function runOperatorCommand(content: string): Promise<void> {
    operatorCommandDraft.value = content.trim();
    setDockHeroMode('command');
    commandFocusToken.value += 1;
    await submitOperatorCommand();
  }

  function applyOperatorDockDefaults(): void {
    if (layoutMode.value !== 'operator') {
      return;
    }

    const next = new Set(expandedDockSeams.value);
    next.add('thread');
    expandedDockSeams.value = next;

    if (!leftSidebarModeTouched.value) {
      leftSidebarMode.value = resolveDefaultLeftSidebarMode({
        pendingApprovals: pendingApprovalsCount.value,
        briefing: operatorBriefing.value,
      });
    }

    if (!dockHeroModeTouched.value) {
      dockHeroMode.value = resolveDefaultDockHeroMode({
        pendingApprovals: pendingApprovalsCount.value,
        criticalSignals: runtimeSummary.value?.signals.critical_count ?? 0,
        highSignals: runtimeSummary.value?.signals.high_count ?? 0,
      });
    }
  }

  function setLeftSidebarMode(mode: LeftSidebarMode): void {
    leftSidebarModeTouched.value = true;
    leftSidebarMode.value = mode;
    persistLeftSidebarMode(mode);
  }

  function setDockHeroMode(mode: DockHeroMode): void {
    dockHeroModeTouched.value = true;
    dockHeroMode.value = mode;
    if (mode === 'briefing') {
      briefingSeamEmphasized.value = false;
    }
  }

  function toggleDockHeroMode(): void {
    setDockHeroMode(dockHeroMode.value === 'command' ? 'briefing' : 'command');
  }

  function focusAttentionSidebar(signalId?: string | null): void {
    setLeftSidebarMode('attention');
    if (signalId) {
      highlightedSignalId.value = signalId;
    } else {
      const signals = operatorBriefing.value?.top_signals ?? [];
      const bootstrap = signals.find((signal) =>
        isBootstrapSummarySignal(signal.signal_id, signal.title),
      );
      highlightedSignalId.value =
        bootstrap?.signal_id ?? (signals.length === 1 ? signals[0]?.signal_id ?? null : null);
    }
    signalsSeamEmphasized.value = true;
    if (typeof window !== 'undefined') {
      window.requestAnimationFrame(() => {
        document.getElementById('dock-seam-signals')?.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest',
        });
        window.setTimeout(() => {
          signalsSeamEmphasized.value = false;
        }, 1200);
      });
    }
  }

  function toggleSignalDetails(signalId: string): void {
    highlightedSignalId.value = highlightedSignalId.value === signalId ? null : signalId;
  }

  function focusMissionControl(): void {
    missionControlEmphasized.value = true;
    if (typeof window !== 'undefined') {
      window.requestAnimationFrame(() => {
        document.getElementById('operator-mission-control')?.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest',
        });
        window.setTimeout(() => {
          missionControlEmphasized.value = false;
        }, 1200);
      });
    }
  }

  function afterRunLifecycleMutation(): void {
    focusMissionControl();
    if (dockHeroMode.value === 'briefing' && typeof window !== 'undefined') {
      briefingSeamEmphasized.value = true;
      window.setTimeout(() => {
        briefingSeamEmphasized.value = false;
      }, 1200);
    }
  }

  function focusKairoBriefing(): void {
    setDockHeroMode('briefing');
    briefingSeamEmphasized.value = true;
    if (typeof window !== 'undefined') {
      window.requestAnimationFrame(() => {
        document.getElementById('dock-seam-briefing')?.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest',
        });
        window.setTimeout(() => {
          briefingSeamEmphasized.value = false;
        }, 1200);
      });
    }
  }

  function focusCommandSeam(example: string): void {
    operatorCommandDraft.value = example;
    setDockHeroMode('command');
    commandFocusToken.value += 1;
    if (typeof window !== 'undefined') {
      window.requestAnimationFrame(() => {
        document.getElementById('operator-command-input')?.focus();
        document.getElementById('dock-seam-briefing')?.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest',
        });
      });
    }
  }

  function syncCurrentWorkspace(preferredWorkspaceId?: string | null): void {
    if (workspaces.value.length === 0) {
      currentWorkspace.value = null;
      return;
    }

    const targetWorkspaceId = resolveOperatorWorkspaceId({
      explicitPreferredId:
        preferredWorkspaceId !== undefined && preferredWorkspaceId !== null
          ? preferredWorkspaceId
          : null,
      pinnedWorkspaceId: operatorPinnedWorkspaceId.value,
      workspaces: workspaces.value,
      activeRun: activeRun.value,
    });

    currentWorkspace.value =
      workspaces.value.find((workspace) => workspace.workspace_id === targetWorkspaceId) ??
      workspaces.value[0] ??
      null;
  }

  function shouldAutoSyncWorkspaceFromRuns(): boolean {
    return !operatorPinnedWorkspaceId.value;
  }

  function setLayoutMode(mode: LayoutMode): void {
    layoutMode.value = mode;
    persistLayoutMode(mode);
    expandedDockSeams.value = new Set();
    dockHeroModeTouched.value = false;
    leftSidebarModeTouched.value = false;
    applyOperatorDockDefaults();
  }

  function revealIdeTerminalPanel(): void {
    persistWorkbenchTerminalPanelVisible('ide', true);
    ideTerminalRevealToken.value += 1;
  }

  function toggleIdeTerminalPanel(): void {
    ideTerminalToggleToken.value += 1;
  }

  function setIdeActivityView(view: IdeActivityView): void {
    ideActivityView.value = view;
    if (view === 'explorer') {
      ideExplorerCollapsed.value = false;
      persistIdeExplorerCollapsed(false);
      return;
    }
    if (view === 'terminal') {
      revealIdeTerminalPanel();
      return;
    }
    if (view === 'agent') {
      agentDockCollapsed.value = false;
      persistAgentDockCollapsed(false);
    }
  }

  function toggleIdeExplorer(): void {
    ideExplorerCollapsed.value = !ideExplorerCollapsed.value;
    persistIdeExplorerCollapsed(ideExplorerCollapsed.value);
    if (!ideExplorerCollapsed.value) {
      ideActivityView.value = 'explorer';
    }
  }

  function toggleAgentDock(): void {
    agentDockCollapsed.value = !agentDockCollapsed.value;
    persistAgentDockCollapsed(agentDockCollapsed.value);
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

  function promptWorkspaceFilePath(message: string, defaultValue = ''): string | null {
    if (typeof window === 'undefined') {
      return null;
    }

    const response = window.prompt(message, defaultValue);
    if (response === null) {
      return null;
    }

    const normalized = normalizeWorkspaceFilePath(response);
    if (!isSafeWorkspaceFilePath(normalized)) {
      workspaceFilesError.value = 'Enter a safe relative path inside the workspace.';
      return null;
    }

    if (!normalized) {
      workspaceFilesError.value = 'File path is required.';
      return null;
    }

    return normalized;
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

  async function createWorkspaceFile(): Promise<void> {
    const workspaceId = currentWorkspace.value?.workspace_id;
    if (!workspaceId) {
      workspaceFilesError.value = 'Select a workspace before creating a file.';
      return;
    }

    workspaceFilesError.value = null;
    const path = promptWorkspaceFilePath('New workspace file path', 'src/new-file.txt');
    if (!path) {
      return;
    }

    if (workspaceFileEntries.value.some((entry) => entry.path === path)) {
      await openWorkspaceFile(path);
      return;
    }

    fileSaveState.value = 'saving';
    fileSaveError.value = null;

    try {
      const payload = await saveWorkspaceFile(workspaceId, path, '');
      workspaceFileEntries.value = [...workspaceFileEntries.value, payload].sort((left, right) =>
        left.path.localeCompare(right.path),
      );
      fileContents.value = {
        ...fileContents.value,
        [path]: '',
      };
      fileSavedContents.value = {
        ...fileSavedContents.value,
        [path]: '',
      };
      fileContentLoadStates.value = {
        ...fileContentLoadStates.value,
        [path]: 'loaded',
      };
      await openWorkspaceFile(path);
    } catch (error) {
      fileSaveError.value = error instanceof Error ? error.message : 'workspace file create failed';
    } finally {
      fileSaveState.value = 'idle';
    }
  }

  async function renameActiveWorkspaceFile(): Promise<void> {
    const workspaceId = currentWorkspace.value?.workspace_id;
    const oldPath = activeWorkspaceFilePath.value;
    if (!workspaceId || !oldPath) {
      workspaceFilesError.value = 'Open a workspace file before renaming it.';
      return;
    }

    workspaceFilesError.value = null;
    const newPath = promptWorkspaceFilePath('Rename workspace file to', oldPath);
    if (!newPath || newPath === oldPath) {
      return;
    }

    fileSaveState.value = 'saving';
    fileSaveError.value = null;

    try {
      const payload = await renameWorkspaceFile(workspaceId, oldPath, newPath);
      workspaceFileEntries.value = workspaceFileEntries.value
        .map((entry) =>
          entry.path === oldPath ? { path: payload.path, size_bytes: payload.size_bytes } : entry,
        )
        .sort((left, right) => left.path.localeCompare(right.path));
      fileContents.value = remapWorkspaceFileRecord(fileContents.value, oldPath, newPath);
      fileSavedContents.value = remapWorkspaceFileRecord(
        fileSavedContents.value,
        oldPath,
        newPath,
      );
      fileContentLoadStates.value = remapWorkspaceFileRecord(
        fileContentLoadStates.value,
        oldPath,
        newPath,
      );
      openedFilePaths.value = remapWorkspaceFilePaths(openedFilePaths.value, oldPath, newPath);
      activeEditorDocumentId.value = workspaceFileDocumentId(newPath);
      await ensureWorkspaceFileLoaded(newPath);
    } catch (error) {
      fileSaveError.value = error instanceof Error ? error.message : 'workspace file rename failed';
    } finally {
      fileSaveState.value = 'idle';
    }
  }

  function setCurrentWorkspace(workspaceId: string): void {
    const previousWorkspaceId = currentWorkspace.value?.workspace_id ?? null;
    operatorPinnedWorkspaceId.value = workspaceId;
    persistOperatorWorkspaceId(workspaceId);
    syncCurrentWorkspace(workspaceId);
    if (previousWorkspaceId !== workspaceId) {
      resetThreadContext();
      void loadWorkspaceThread(workspaceId);
      void loadRunHistory(selectWorkspacePrimaryRun(
        runs.value.filter((run) => run.workspace_id === workspaceId),
      )?.run_id ?? null);
    }
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

  async function loadWorkspaces(options: { sync?: boolean } = {}): Promise<void> {
    workspacesLoadState.value = 'loading';
    workspacesError.value = null;

    try {
      const snapshot = await fetchWorkspaces();
      workspaces.value = mergeOperatorWorkspaceCatalog(snapshot.items);
      const visibleIds = new Set(workspaces.value.map((workspace) => workspace.workspace_id));
      if (
        operatorPinnedWorkspaceId.value &&
        !visibleIds.has(operatorPinnedWorkspaceId.value)
      ) {
        operatorPinnedWorkspaceId.value = null;
        persistOperatorWorkspaceId(null);
      }
      if (options.sync !== false && shouldAutoSyncWorkspaceFromRuns()) {
        syncCurrentWorkspace();
      }
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

  async function loadConnectors(): Promise<void> {
    connectorsLoadState.value = 'loading';
    connectorsError.value = null;

    try {
      const snapshot = await fetchConnectors();
      connectorsItems.value = snapshot.items;
      connectorsSummary.value = snapshot.summary;
      connectorsLoadState.value = 'loaded';
    } catch (error) {
      connectorsLoadState.value = 'error';
      connectorsError.value =
        error instanceof Error ? error.message : 'connectors request failed';
    }
  }

  async function reprobeConnector(connectorId: string): Promise<void> {
    connectorMutationPending.value = true;
    connectorsError.value = null;

    try {
      await postWatchCommand({
        command_type: 'reprobe_connector',
        target_type: 'connector',
        target_id: connectorId,
        requested_by: 'operator',
      });
      await Promise.all([loadConnectors(), loadRuntimeSummary(), loadInbox()]);
    } catch (error) {
      connectorsError.value =
        error instanceof Error ? error.message : 'connector reprobe failed';
    } finally {
      connectorMutationPending.value = false;
    }
  }

  async function refreshWatchSummary(): Promise<void> {
    connectorMutationPending.value = true;
    connectorsError.value = null;

    try {
      await postWatchCommand({
        command_type: 'refresh_summary',
        requested_by: 'operator',
      });
      await Promise.all([
        loadConnectors(),
        loadRuntimeSummary(),
        loadInbox(),
        loadOperatorBriefing(),
      ]);
    } catch (error) {
      connectorsError.value =
        error instanceof Error ? error.message : 'watch summary refresh failed';
    } finally {
      connectorMutationPending.value = false;
    }
  }

  async function loadOperatorPresenceSettings(): Promise<void> {
    const cached = readPersistedOperatorPresenceSettings();
    if (cached) {
      operatorPresenceSettings.value = cached;
    }

    try {
      const snapshot = await fetchOperatorPresenceSettings();
      operatorPresenceSettings.value = normalizeOperatorPresenceSettings(snapshot.settings);
      persistOperatorPresenceSettings(operatorPresenceSettings.value);
    } catch {
      // Keep cached defaults when settings API is unavailable during bootstrap.
    }
  }

  async function saveOperatorPresenceSettingsPatch(
    patch: Partial<OperatorPresenceSettings>,
  ): Promise<void> {
    operatorPresenceSettingsSaving.value = true;
    const nextSettings = normalizeOperatorPresenceSettings({
      ...operatorPresenceSettings.value,
      ...patch,
    });
    operatorPresenceSettings.value = nextSettings;
    persistOperatorPresenceSettings(nextSettings);

    try {
      const snapshot = await saveOperatorPresenceSettings(patch);
      operatorPresenceSettings.value = normalizeOperatorPresenceSettings(snapshot.settings);
      persistOperatorPresenceSettings(operatorPresenceSettings.value);
      await loadOperatorBriefing();
    } catch (error) {
      operatorPresenceSettings.value = nextSettings;
      briefingError.value =
        error instanceof Error ? error.message : 'operator presence settings save failed';
    } finally {
      operatorPresenceSettingsSaving.value = false;
    }
  }

  function toggleOperatorPresenceSettingsPanel(forceOpen?: boolean): void {
    operatorPresenceSettingsOpen.value =
      typeof forceOpen === 'boolean' ? forceOpen : !operatorPresenceSettingsOpen.value;
  }

  async function loadOperatorBriefing(options?: { viewportCompact?: boolean }): Promise<void> {
    briefingLoadState.value = 'loading';
    briefingError.value = null;

    const viewportCompact =
      options?.viewportCompact ??
      shouldRequestViewportCompactBriefing(
        viewportWidth.value,
        operatorBriefing.value?.operator_presence ?? null,
        operatorPresenceSettings.value,
      );

    try {
      operatorBriefing.value = await fetchOperatorBriefing({ viewportCompact });
      lastViewportCompactRequested = viewportCompact;
      approvals.value = operatorBriefing.value.pending_approvals.items;
      briefingLoadState.value = 'loaded';
      if (operatorBriefing.value.operator_presence?.spoken_alert) {
        deliverSpokenOperatorAlert(operatorBriefing.value.operator_presence.spoken_alert);
      }
      applyOperatorDockDefaults();
    } catch (error) {
      briefingLoadState.value = 'error';
      briefingError.value =
        error instanceof Error ? error.message : 'operator briefing request failed';
    }
  }

  function syncViewportCompactFromResize(): void {
    if (typeof window === 'undefined') {
      return;
    }

    viewportWidth.value = readViewportWidth(window);
    const shouldRequest = shouldRequestViewportCompactBriefing(
      viewportWidth.value,
      operatorBriefing.value?.operator_presence ?? null,
      operatorPresenceSettings.value,
    );
    if (shouldRequest === lastViewportCompactRequested) {
      return;
    }
    void loadOperatorBriefing({ viewportCompact: shouldRequest });
  }

  function bindViewportCompactListener(): void {
    if (typeof window === 'undefined' || viewportCompactListenerBound) {
      return;
    }
    viewportWidth.value = readViewportWidth(window);
    window.addEventListener('resize', syncViewportCompactFromResize);
    viewportCompactListenerBound = true;
  }

  function unbindViewportCompactListener(): void {
    if (typeof window === 'undefined' || !viewportCompactListenerBound) {
      return;
    }
    window.removeEventListener('resize', syncViewportCompactFromResize);
    viewportCompactListenerBound = false;
  }

  async function loadRuns(options: { sync?: boolean } = {}): Promise<void> {
    runsLoadState.value = 'loading';
    runsError.value = null;

    try {
      const snapshot = await fetchRuns();
      runs.value = snapshot.items;
      activeRun.value = selectPrimaryRun(snapshot.items);
      if (options.sync !== false && shouldAutoSyncWorkspaceFromRuns()) {
        syncCurrentWorkspace(activeRun.value?.workspace_id ?? null);
      }
      runsLoadState.value = 'loaded';
    } catch (error) {
      runsLoadState.value = 'error';
      runsError.value = error instanceof Error ? error.message : 'runs request failed';
    }
  }

  async function loadRunHistory(runId: string | null): Promise<void> {
    if (!runId) {
      runHistorySnapshot.value = null;
      runHistoryLoadState.value = 'idle';
      return;
    }

    runHistoryLoadState.value = 'loading';
    try {
      runHistorySnapshot.value = await fetchRunHistory(runId);
      runHistoryLoadState.value = 'loaded';
    } catch {
      runHistorySnapshot.value = null;
      runHistoryLoadState.value = 'error';
    }
  }

  async function refreshRunSurfaces(): Promise<void> {
    await Promise.all([
      loadRuns(),
      loadRuntimeSummary(),
      loadInbox(),
      loadConnectors(),
      loadOperatorBriefing(),
    ]);
    await loadRunHistory(primaryActiveRun.value?.run_id ?? null);
  }

  async function stopPrimaryRun(): Promise<void> {
    const run = primaryActiveRun.value;
    if (!run?.can_stop || runMutationPending.value) {
      return;
    }

    runMutationState.value = 'stopping';
    runMutationError.value = null;

    try {
      await stopRun(run.run_id);
      await refreshRunSurfaces();
      afterRunLifecycleMutation();
    } catch (error) {
      runMutationError.value = error instanceof Error ? error.message : 'stop run request failed';
    } finally {
      runMutationState.value = 'idle';
    }
  }

  async function resumePrimaryRun(): Promise<void> {
    const run = primaryActiveRun.value;
    if (!run?.can_resume || runMutationPending.value) {
      return;
    }

    runMutationState.value = 'resuming';
    runMutationError.value = null;

    try {
      await resumeRun(run.run_id);
      await refreshRunSurfaces();
      afterRunLifecycleMutation();
    } catch (error) {
      runMutationError.value = error instanceof Error ? error.message : 'resume run request failed';
    } finally {
      runMutationState.value = 'idle';
    }
  }

  async function markPrimaryRunReviewReady(): Promise<void> {
    const run = primaryActiveRun.value;
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
    const run = primaryActiveRun.value;
    if (!run || !isOperatorCompletablePhase(run.phase) || runMutationPending.value) {
      return;
    }

    runMutationState.value = 'completing';
    runMutationError.value = null;

    try {
      await completeRun(run.run_id);
      await refreshRunSurfaces();
      afterRunLifecycleMutation();
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

  async function clearActiveSignals(): Promise<void> {
    const signalIds =
      operatorBriefing.value?.top_signals.map((signal) => signal.signal_id) ??
      signalViews.value.map((signal) => signal.signal_id);
    if (!signalIds.length || signalClearState.value === 'clearing') {
      return;
    }

    signalClearState.value = 'clearing';
    signalClearError.value = null;
    highlightedSignalId.value = null;

    try {
      await acknowledgeInboxSignals(signalIds);
      await Promise.all([loadInbox(), loadOperatorBriefing(), loadRuntimeSummary()]);
    } catch (error) {
      signalClearError.value =
        error instanceof Error ? error.message : 'clear signals request failed';
    } finally {
      signalClearState.value = 'idle';
    }
  }

  async function loadBootstrapData(): Promise<void> {
    await loadOperatorPresenceSettings();
    await Promise.all([
      loadRuntimeSummary(),
      loadInbox(),
      loadConnectors(),
      loadOperatorBriefing(),
    ]);
    await loadWorkspaces({ sync: false });
    await loadRuns({ sync: false });
    syncCurrentWorkspace(
      operatorPinnedWorkspaceId.value ??
        defaultOperatorWorkspaceId(workspaces.value),
    );
    await loadRunHistory(primaryActiveRun.value?.run_id ?? null);
    await loadWorkspaceFiles();
    const workspaceId = currentWorkspace.value?.workspace_id;
    if (workspaceId) {
      await loadWorkspaceThread(workspaceId);
    }
    applyOperatorDockDefaults();
  }

  return {
    activeEditorTabId,
    activeEditorDocument,
    activeEditorDocumentId,
    activeRun,
    activeTerminalSessionId,
    activeWorkspaceFilePath,
    approvePrimaryRun,
    approvalsSummaryLabel,
    approvals,
    briefingError,
    briefingLoadState,
    briefingSeamEmphasized,
    missionControlEmphasized,
    signalsSeamEmphasized,
    highlightedSignalId,
    briefingSummaryLine,
    canApprovePrimaryRun,
    canCompletePrimaryRun,
    canMarkPrimaryRunReviewReady,
    canRejectPrimaryRun,
    currentWorkspace,
    editorDocuments,
    canResumePrimaryRun,
    canStopPrimaryRun,
    canSubmitOperatorCommand,
    commandMutationError,
    commandMutationState,
    commandFocusToken,
    commandSeamHint,
    dockContext,
    dockHeroMode,
    dockSeamLayout,
    dockSeamState,
    editorTabs,
    inboxError,
    inboxItems,
    inboxLoadState,
    inboxStateLabel,
    kairoBriefingAttention,
    kairoBriefingAttentionLabel,
    kairoPresenceState,
    agentDockCollapsed,
    ideActivityView,
    ideExplorerCollapsed,
    ideTerminalRevealToken,
    ideTerminalToggleToken,
    layoutMode,
    layoutModeLabel,
    leftSidebarAttentionBadgeCount,
    leftSidebarMode,
    mobileCompactLayout,
    viewportWidth,
    clearActiveSignals,
    completePrimaryRun,
    connectorMutationPending,
    connectorsError,
    connectorsItems,
    connectorsLoadState,
    connectorsSummary,
    bindViewportCompactListener,
    unbindViewportCompactListener,
    loadBootstrapData,
    loadConnectors,
    loadInbox,
    loadOperatorBriefing,
    loadOperatorPresenceSettings,
    loadRuns,
    loadRuntimeSummary,
    loadWorkspaces,
    markPrimaryRunReviewReady,
    operatorBriefing,
    operatorCommandDraft,
    operatorPresenceSettings,
    operatorPresenceSettingsOpen,
    operatorPresenceSettingsSaving,
    createWorkspaceFile,
    pendingApprovalsCount,
    primaryActiveRun,
    primaryApprovalRun,
    primaryInboxItem,
    refreshRunSurfaces,
    refreshWatchSummary,
    rejectPrimaryRun,
    reprobeConnector,
    runOperatorCommand,
    resumePrimaryRun,
    runs,
    runsError,
    runsLoadState,
    runMutationError,
    runHistoryRows,
    runHistoryLoadState,
    runMutationPending,
    runMutationState,
    runStateLabel,
    runtimeStateLabel,
    runtimeSummary,
    runtimeSummaryError,
    runtimeSummaryLoadState,
    showDevSeams,
    showKairoBriefingAttention,
    statusBarItems,
    statusBarSegments,
    statusBarZones,
    renameActiveWorkspaceFile,
    setActiveEditorTab,
    setActiveEditorDocument,
    setCurrentWorkspace,
    setDockHeroMode,
    setIdeActivityView,
    setLayoutMode,
    setLeftSidebarMode,
    toggleAgentDock,
    toggleIdeExplorer,
    signalClearError,
    signalClearState,
    signalViews,
    stopPrimaryRun,
    submitOperatorCommand,
    terminalSessions,
    threadMessages,
    threadStateLabel,
    toggleDockSeam,
    toggleDockHeroMode,
    toggleOperatorPresenceSettingsPanel,
    toggleSignalDetails,
    topbarBreadcrumb,
    topbarChips,
    topbarMetaPills,
    fileSaveError,
    fileSaveState,
    focusCommandSeam,
    focusAttentionSidebar,
    focusMissionControl,
    focusKairoBriefing,
    loadWorkspaceFiles,
    openWorkspaceFile,
    saveActiveFileDocument,
    saveOperatorPresenceSettingsPatch,
    updateActiveFileContent,
    workspaceFileEntries,
    workspaceFilesError,
    workspaceFilesLoadState,
    workspacesError,
    workspacesLoadState,
    workspacePrimarySignal,
    workspaceStateLabel,
    workspaceStatusCardRows,
    workspaceTrailLabel,
    workspaces,
    usesProductionWorkspaceCatalog,
  };
});
