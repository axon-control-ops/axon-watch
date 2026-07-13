import { computed, ref, watch, type ComputedRef } from 'vue';
import { defineStore } from 'pinia';

import {
  approveRun,
  completeRun,
  fetchThreadHistory,
  fetchWorkspaceChatThread,
  hasWorkspaceChatThread,
  fetchWorkspaceFile,
  fetchWorkspaceFiles,
  markRunReviewReady,
  createWorkspaceChatThread,
  createWorkspaceHandoff,
  fetchWorkspaceChatThreads,
  uploadChatAttachment,
  postChatMessage,
  rejectRun,
  resumeRun,
  saveWorkspaceFile,
  stopRun,
} from '../api/control-plane';
import type {
  ConnectorProbeRecord,
  CursorRuntimeStatusSnapshot,
  FleetHealthSnapshot,
  RuntimeMcpToolsSnapshot,
  TerminalSessionRecord,
  WorkspaceChatThreadListItem,
} from '../api/control-plane';
import {
  readStoredOperatorCenterView,
  type BrainGraphSnapshot,
  type OperatorCenterView,
} from '../lib/operator-brain-graph-view';
import { resolveSignalHandoff, type SignalHandoffInput } from '../lib/signal-handoff-view';
import {
  readPendingHandoffDismissSignalId,
  writePendingHandoffDismissSignalId,
} from '../lib/signal-handoff-dismiss';
import type { RuntimeStatusSnapshot } from '../api/control-plane';
import type {
  ApprovalRecord,
  InboxItem,
  OperatorBriefing,
  OperatorPresenceSettings,
  RunRecord,
  RuntimeSummary,
  SignalView,
  SpokenAlertEligibility,
  WorkspaceRecord,
} from '../contracts/canonical';
import { deliverSpokenOperatorAlert } from '../lib/spoken-alert-delivery';
import {
  editedFilePathsFromTranscript,
} from '../lib/agent-transcript-blocks';
import { buildResearchEditorContent } from '../lib/prove-research-source';
import { resolveResearchFlyToTarget } from '../lib/research-fly-to-source';
import type { ResearchBlockKind } from '../lib/research-provider';
import { createAgentStreamIncrementalState } from '../lib/agent-stream-incremental';
import { narrationForCompletion } from '../lib/kairo-agent-narration';
import { createRafStreamUiBatcher } from '../lib/stream-ui-raf-batch';
import {
  resolveBootstrapIdeThreadId,
  shouldApplyWorkspaceThreadLoad,
} from '../lib/workspace-thread-load';
import {
  createWorkspaceThreadLoadQueue,
  loadWorkspaceThreadOnce,
} from '../lib/load-workspace-thread';
import { createKairoAgentMilestoneNarrator } from '../lib/kairo-agent-milestone-narrator';
import { effectiveKairoNarration, shouldSpeakLiveThinkingBlock } from '../lib/kairo-narration-policy';
import { createKairoProgressNarrator } from '../lib/kairo-progress-narrator';
import { postKairoSpeak } from '../lib/kairo-speak-client';
import type { EditorRevealRequest } from '../components/EditorHost.vue';
import type { EditorSelectionSnapshot } from '../lib/create-monaco-editor';
import {
  DEFAULT_OPERATOR_TERMINAL_SESSION_ID,
} from '../lib/terminal-session-view';
import {
  createTerminalSessionStore,
  DEFAULT_TERMINAL_SESSIONS,
  type TerminalSessionDescriptor,
} from '../lib/shell-terminal-session-store';
import { createWorkspaceFileOps } from '../lib/shell-workspace-file-ops';
import { sortIdeThreadsNewestFirst } from '../lib/ide-thread-picker-view';
import {
  ensureOpenIdeThreadTabs,
  openIdeThreadTab,
  pruneOpenIdeThreadTabs,
  resolveIdeThreadTabAfterClose,
  resolveOpenIdeThreadTabItems,
} from '../lib/ide-thread-tabs-view';
import {
  readOpenIdeThreadIdsByWorkspace,
  writeOpenIdeThreadIdsForWorkspace,
} from '../lib/ide-thread-tabs-prefs';
import { ideVoiceSpeechAllowed } from '../lib/ide-voice-strip';
import { buildKairoSpeechSessionId } from '../lib/kairo-speech-session';
import {
  appendBriefingVoiceTranscriptEntry,
  readBriefingVoiceTranscript,
  type BriefingVoiceTranscriptEntry,
} from '../lib/briefing-voice-transcript';
import {
  onKairoVoiceIdle,
  pauseKairoPlayback,
  resumeKairoPlayback,
  speakKairoLine,
  stopKairoPlayback,
  subscribeKairoVoiceSpeaking,
  isKairoVoiceSpeaking,
} from '../lib/kairo-voice-playback';
import {
  flushKairoSpeechQueue,
  interruptKairoSpeechQueue,
  isKairoSpeechQueueBusy,
} from '../lib/kairo-voice-queue';
import {
  onSpeechQueueIdle,
  subscribeSpeechQueueSpeaking,
} from '../lib/speech-queue';
import {
  setKairoConversationPhase,
  kairoConversationPhase,
} from '../features/kairo-conversation/kairo-conversation-state';
import { scheduleBriefingSurfaceOffer } from '../features/kairo-conversation/conversation-briefing-surface';
import {
  normalizeAgentExecutionAccess,
  persistAgentExecutionAccess,
  resolveAgentExecutionAccess,
  clearFullAccessSessionConsent,
  markFullAccessSessionConsent,
  type AgentExecutionAccess,
} from '../lib/agent-execution-access-prefs';
import {
  buildIdeComposerActivityLabel,
  buildIdeStreamActivityLabel,
  type IdeComposerActivity,
} from '../lib/agent-dock-activity-view';
import {
  resolveIdeAgentLinkedRunId,
  resolveIdeAgentLinkedRunIdFromMessages,
} from '../lib/ide-agent-run-link';
import { resolveLatestWorkspaceAgentContent } from '../lib/ide-agent-center-view';
import {
  shouldClearIdeAgentRunLink,
} from '../lib/ide-agent-run-active';
import { resolveComposerContextPayload } from '../lib/ide-composer-context-tokens';
import {
  appendIdeComposerQueueEntry,
  ideComposerQueueLabel as buildIdeComposerQueueLabel,
  removeIdeComposerQueueEntry,
  shiftIdeComposerQueue,
  shouldQueueIdeComposerSubmit,
  type IdeComposerMode,
  type IdeComposerQueuedMessage,
} from '../lib/ide-composer-queue';
import {
  persistIdeComposerDraft,
  readStoredIdeComposerDraft,
} from '../lib/ide-composer-draft-prefs';
import {
  defaultWorkspaceStreamUi,
  shouldSyncWorkspaceStreamGlobals,
  workspaceStreamGlobalsFromState,
} from '../lib/workspace-stream-ui';
import { resolveKairoPresenceClickTarget } from '../lib/kairo-presence-action';
import { isBootstrapSummarySignal } from '../lib/operator-signal-hints';
import {
  readViewportWidth,
} from '../lib/viewport-compact';
import {
  defaultOperatorPresenceSettings,
  readPersistedOperatorPresenceSettings,
} from '../lib/operator-presence-settings';
import {
  buildRunHistoryRows,
  type RunHistorySnapshot,
} from '../lib/run-history-view';
import { isOperatorCompletablePhase } from '../lib/run-lifecycle-ui';
import {
  appendOperatorCommand,
  canSubmitOperatorCommand as canSubmitOperatorCommandDraft,
  commandSeamHint as buildCommandSeamHint,
  mapChatMessageRecord,
  mergeThreadMessages,
  type OperatorThreadEntry,
} from '../lib/operator-thread';
import {
  filterThreadMessagesForSurface,
  type ThreadSurface,
} from '../lib/thread-surface-view';
import {
  applyChatUiAction,
  parseChatUiAction,
} from '../lib/chat-ui-action';
import {
  startChatStreamSession,
  type ChatStreamSession,
} from '../lib/chat-stream-session';
import {
  filePathFromDocumentId,
  languageForFilePath,
  isImageFilePath,
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
  type EditorDocumentLanguage,
  type WorkspaceDocumentDescriptor,
} from '../lib/workspace-documents';
import { persistEditorMarkdownPreviewEnabled } from '../lib/editor-markdown-preview-prefs';
import {
  readActiveEditorDocumentIdsByWorkspace,
  readOpenEditorFilePathsByWorkspace,
  resolveRestoredActiveEditorDocumentId,
  restoreOpenEditorFilePaths,
  writeActiveEditorDocumentIdForWorkspace,
  writeOpenEditorFilePathsForWorkspace,
} from '../lib/editor-open-tabs-prefs';
import { formatAgentDraftTitle } from '../lib/editor-tab-labels';
import type { IdeAgentEditSummary } from '../lib/ide-agent-center-view';
import {
  agentEditReviewDocumentId,
  agentEditReviewDocumentTitle,
  formatAgentEditReviewContent,
  isAgentEditReviewDocumentId,
  isMarkdownAgentEditPath,
  shouldOpenWorkspaceFileForEditReview,
} from '../lib/ide-agent-edit-review';
import { normalizeEditedFilePath } from '../lib/agent-transcript-blocks';
import {
  selectWorkspacePrimaryRun,
} from './shell-run-selection';
import { resolveKairoPresenceState, type KairoPresenceState } from '../lib/kairo-presence';
import {
  ideDisplayKairoState,
  resolveIdePresenceProfile,
  type IdePresenceProfile,
} from '../lib/ide-presence-profile';
import {
  buildDockSeamLayout,
  type DockSeamId,
} from '../lib/dock-seam-layout';
import {
  readStoredDockHeroMode,
} from '../lib/dock-hero-prefs';
import {
  type DockHeroMode,
} from '../lib/dock-hero-mode';
import {
  readStoredLeftSidebarMode,
  type LeftSidebarMode,
} from '../lib/left-sidebar-mode';
import {
  briefingAttentionStatusLabel,
  resolveKairoBriefingAttention,
  shouldShowBriefingAttentionInCommandMode,
} from '../lib/kairo-briefing-attention';
import {
  buildStatusBarSegments,
} from '../lib/runtime-strip';
import {
  persistOperatorWorkspaceId,
  readStoredOperatorWorkspaceId,
} from '../lib/operator-workspace-selection';
import {
  defaultOperatorWorkspaceId,
} from '../lib/operator-workspace-catalog';
import {
  type IdeActivityView,
  persistAgentDockCollapsed,
  persistLayoutMode,
  readStoredAgentDockCollapsed,
  readStoredIdeExplorerCollapsed,
  readStoredLayoutMode,
} from '../lib/ide-layout-prefs';
import { createCatalogLoadersSlice } from './shell/slices/create-catalog-loaders-slice';
import { createComposerRuntimePrefsSlice } from './shell/slices/create-composer-runtime-prefs-slice';
import { createConnectorsSlice } from './shell/slices/create-connectors-slice';
import { createCursorCatalogSlice } from './shell/slices/create-cursor-catalog-slice';
import { createDockLayoutSlice } from './shell/slices/create-dock-layout-slice';
import { createIdeWorkbenchChromeSlice } from './shell/slices/create-ide-workbench-chrome-slice';
import { createOperatorBriefingSlice } from './shell/slices/create-operator-briefing-slice';
import { createOperatorFocusSlice } from './shell/slices/create-operator-focus-slice';
import { createOperatorPresenceSettingsSlice } from './shell/slices/create-operator-presence-settings-slice';
import { createOperatorProbesSlice } from './shell/slices/create-operator-probes-slice';
import { createInboxSignalsSlice } from './shell/slices/create-inbox-signals-slice';
import { createRuntimeProbesSlice } from './shell/slices/create-runtime-probes-slice';
import { createRuntimeSummarySlice } from './shell/slices/create-runtime-summary-slice';
import { createShellDisplaySlice } from './shell/slices/create-shell-display-slice';
import { createThreadSurfaceSlice } from './shell/slices/create-thread-surface-slice';
import { createViewportCompactSlice } from './shell/slices/create-viewport-compact-slice';
import {
  DEFAULT_DOCK_CONTEXT,
  DEFAULT_EDITOR_TABS,
  hydrateWorkspaceSurfaceThreadIds,
  type BriefingLoadState,
  type DockContextDescriptor,
  type EditorTabDescriptor,
  type InboxLoadState,
  type LayoutMode,
  type RunMutationState,
  type RuntimeStatusLoadState,
  type RuntimeSummaryLoadState,
  type RunsLoadState,
  type WorkspaceFilesLoadState,
  type WorkspacesLoadState,
} from './shell/types';
export type { LayoutMode, RuntimeSummaryLoadState, RuntimeStatusLoadState, InboxLoadState, RunsLoadState, WorkspacesLoadState, BriefingLoadState, WorkspaceFilesLoadState, RunMutationState } from './shell/types';

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
  const runtimeStatus = ref<RuntimeStatusSnapshot | null>(null);
  const runtimeStatusLoadState = ref<RuntimeStatusLoadState>('idle');
  const runtimeMcpTools = ref<RuntimeMcpToolsSnapshot | null>(null);
  const runtimeMcpToolsLoadState = ref<RuntimeStatusLoadState>('idle');
  const runtimeStatusError = ref<string | null>(null);
  const cursorRuntimeStatus = ref<CursorRuntimeStatusSnapshot | null>(null);
  const cursorCatalogLoadState = ref<'idle' | 'loading' | 'loaded' | 'error'>('idle');
  const cursorCatalogError = ref<string | null>(null);
  const agentStreamActive = ref(false);
  const agentStreamMessageId = ref<string | null>(null);
  type AgentReportEditorLink = {
    title: string;
    documentId: string;
  };
  const agentReportEditorLinksByMessageId = ref<Record<string, AgentReportEditorLink>>({});
  const editorRevealRequest = ref<EditorRevealRequest | null>(null);
  type WorkspaceStreamUiState = {
    active: boolean;
    messageId: string | null;
    activity: IdeComposerActivity | null;
    ideAgentRunId: string | null;
  };
  const workspaceStreamUiById = ref<Record<string, WorkspaceStreamUiState>>({});
  const workspaceIdeThreadMessagesById = ref<Record<string, OperatorThreadEntry[]>>({});
  const chatStreamSessionsByWorkspace = new Map<string, ChatStreamSession>();
  const composerRuntimePrefsRevision = ref(0);
  const cursorPickerVisibleRevision = ref(0);
  const activeRun = ref<RunRecord | null>(null);
  const runs = ref<RunRecord[]>([]);
  const runsLoadState = ref<RunsLoadState>('idle');
  const runsError = ref<string | null>(null);
  const runMutationState = ref<RunMutationState>('idle');
  const runMutationError = ref<string | null>(null);
  const signalClearState = ref<'idle' | 'clearing'>('idle');
  const signalClearError = ref<string | null>(null);
  const handoffMutationState = ref<'idle' | 'submitting' | 'error'>('idle');
  const handoffMutationError = ref<string | null>(null);
  const lastDiscussedSignal = ref<SignalHandoffInput | null>(null);
  const pendingHandoffDismissSignalId = ref<string | null>(readPendingHandoffDismissSignalId());
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
  const operatorFleetHealth = ref<FleetHealthSnapshot | null>(null);
  const operatorFleetHealthLoadState = ref<'idle' | 'loading' | 'loaded' | 'error'>('idle');
  const operatorFleetHealthError = ref<string | null>(null);
  const operatorBrainGraph = ref<BrainGraphSnapshot | null>(null);
  const operatorBrainGraphLoadState = ref<'idle' | 'loading' | 'loaded' | 'error'>('idle');
  const operatorBrainGraphError = ref<string | null>(null);
  const operatorCenterView = ref<OperatorCenterView>(readStoredOperatorCenterView());
  const operatorBrainGalaxyActive = computed(() => operatorCenterView.value === 'graph');
  const operatorPresenceSettings = ref<OperatorPresenceSettings>(
    readPersistedOperatorPresenceSettings() ?? defaultOperatorPresenceSettings(),
  );
  const operatorPresenceSettingsOpen = ref(false);
  const operatorPresenceSettingsSaving = ref(false);
  const operatorPresenceSettingsError = ref<string | null>(null);
  const operatorPresenceSettingsSavedAt = ref<number | null>(null);
  const viewportWidth = ref(readViewportWidth());
  const briefingLoadState = ref<BriefingLoadState>('idle');
  const briefingError = ref<string | null>(null);
  const briefingVoiceTranscript = ref<BriefingVoiceTranscriptEntry[]>(readBriefingVoiceTranscript());
  const signalViews = ref<SignalView[]>([]);
  const threadMessages = ref<OperatorThreadEntry[]>([]);
  const operatorThreadMessages = ref<OperatorThreadEntry[]>([]);
  const activeThreadId = ref<string | null>(null);
  const workspaceSurfaceThreadIds = ref<
    Record<string, Partial<Record<ThreadSurface, string>>>
  >(hydrateWorkspaceSurfaceThreadIds());
  const operatorCommandDraft = ref('');
  const ideComposerDraft = ref('');
  let ideComposerDraftPersistTimer: ReturnType<typeof setTimeout> | null = null;
  const kairoSpeechQueueActive = ref(false);
  const kairoVoiceEngineActive = ref(false);
  const kairoVoicePaused = ref(false);
  const ideComposerQueueByWorkspaceId = ref<Record<string, IdeComposerQueuedMessage[]>>({});
  let flushingIdeComposerQueue = false;
  const agentExecutionAccess = ref<AgentExecutionAccess>(resolveAgentExecutionAccess());
  const ideAgentRunId = ref<string | null>(null);
  const ideComposerActivity = ref<IdeComposerActivity | null>(null);
  const ideAgentLinkedRun = computed(() => {
    const runId = ideAgentRunId.value;
    if (!runId) {
      return null;
    }
    return runs.value.find((run) => run.run_id === runId) ?? null;
  });
  const commandMutationState = ref<'idle' | 'submitting' | 'error'>('idle');
  const commandMutationError = ref<string | null>(null);
  const workspaceFileEntries = ref<Array<{ path: string; size_bytes: number }>>([]);
  const workspaceFilesLoadState = ref<WorkspaceFilesLoadState>('idle');
  const workspaceFilesError = ref<string | null>(null);
  const fileContents = ref<Record<string, string>>({});
  const fileSavedContents = ref<Record<string, string>>({});
  const fileContentLoadStates = ref<Record<string, FileContentLoadState>>({});
  const openedFilePaths = ref<string[]>([]);
  const draftDocuments = ref<WorkspaceDocumentDescriptor[]>([]);
  const fileSaveState = ref<'idle' | 'saving'>('idle');
  const fileSaveError = ref<string | null>(null);

  // UI shell scaffolding is local and intentionally placeholder-only.
  const editorTabs = ref<EditorTabDescriptor[]>(DEFAULT_EDITOR_TABS);
  const activeEditorTabId = ref<string>(DEFAULT_EDITOR_TABS[0].id);
  const activeEditorDocumentId = ref<string>('file:README.md');
  const editorSelection = ref<EditorSelectionSnapshot | null>(null);
  const terminalSessions = ref<TerminalSessionDescriptor[]>(DEFAULT_TERMINAL_SESSIONS);
  const activeTerminalSessionId = ref<string>(DEFAULT_OPERATOR_TERMINAL_SESSION_ID);
  const ideThreadsByWorkspaceId = ref<Record<string, WorkspaceChatThreadListItem[]>>({});
  const openIdeThreadIdsByWorkspaceId = ref<Record<string, string[]>>(
    readOpenIdeThreadIdsByWorkspace(),
  );
  const dockContext = ref<DockContextDescriptor>(DEFAULT_DOCK_CONTEXT);
  const expandedDockSeams = ref<Set<DockSeamId>>(new Set(['thread']));
  const dockThreadSeamTouched = ref(false);
  const briefingSeamEmphasized = ref(false);
  const missionControlEmphasized = ref(false);
  const signalsSeamEmphasized = ref(false);
  const highlightedSignalId = ref<string | null>(null);
  const dockHeroMode = ref<DockHeroMode>(readStoredDockHeroMode() ?? 'command');
  const dockHeroModeTouched = ref(readStoredDockHeroMode() !== null);
  const commandFocusToken = ref(0);
  const leftSidebarMode = ref<LeftSidebarMode>(readStoredLeftSidebarMode() ?? 'workspaces');
  const leftSidebarModeTouched = ref(Boolean(readStoredLeftSidebarMode()));
  const ideActivityView = ref<IdeActivityView>('explorer');
  const ideExplorerCollapsed = ref(readStoredIdeExplorerCollapsed());
  const ideAttentionPanelOpen = ref(false);
  const ideBriefingPanelOpen = ref(false);
  const agentDockCollapsed = ref(readStoredAgentDockCollapsed());
  const ideTerminalRevealToken = ref(0);
  const ideTerminalToggleToken = ref(0);


  const layoutModeLabel = computed(() =>
    layoutMode.value === 'operator' ? 'Mission Control' : 'IDE mode',
  );

  const workspaceRuns = computed(() =>
    currentWorkspace.value
      ? runs.value.filter((run) => run.workspace_id === currentWorkspace.value?.workspace_id)
      : runs.value,
  );
  const primaryActiveRun = computed(() => selectWorkspacePrimaryRun(workspaceRuns.value));

  let idePresenceProfile: ComputedRef<IdePresenceProfile>;

  const {
    workspaceTrailLabel,
    workspaceStateLabel,
    usesProductionWorkspaceCatalog,
    topbarChips,
    topbarMetaPills,
    topbarBreadcrumb,
    activeOperatorSignalCount,
    attentionSignals,
    workspaceAttentionSignalCount,
    statusBarZones,
    workspaceStatusCardRows,
    briefingSummaryLine,
    runtimeStateLabel,
    runStateLabel,
    runMutationPending,
    activeIdeStopRun,
    canStopIdeAgentRun,
    canStopPrimaryRun,
    canResumePrimaryRun,
    canMarkPrimaryRunReviewReady,
    canCompletePrimaryRun,
    primaryApprovalRun,
    primaryInboxItem,
    inboxStateLabel,
    approvalsSummaryLabel,
    canApprovePrimaryRun,
    canApproveIdeAgentRun,
    canResumeIdeAgentRun,
    canRejectPrimaryRun,
    threadStateLabel,
    pendingApprovalsCount,
    leftSidebarAttentionBadgeCount,
  } = createShellDisplaySlice({
    currentWorkspace,
    workspaces,
    runtimeSummary,
    runtimeSummaryLoadState,
    activeRun,
    primaryActiveRun,
    layoutMode,
    getIdePresenceProfile: () => idePresenceProfile.value,
    inboxItems,
    inboxLoadState,
    operatorBriefing,
    runs,
    runsLoadState,
    runMutationState,
    ideAgentLinkedRun,
    ideAgentRunId,
    agentStreamActive,
    operatorThreadMessages,
    threadMessages,
  });

  const runHistoryRows = computed(() => buildRunHistoryRows(runHistorySnapshot.value));

  const currentWorkspaceIdeThreadMessages = computed(() => {
    const workspaceId = currentWorkspace.value?.workspace_id;
    if (!workspaceId) {
      return [];
    }
    if (layoutMode.value === 'ide') {
      return threadMessages.value;
    }
    return workspaceIdeThreadMessagesById.value[workspaceId] ?? [];
  });

  const latestWorkspaceAgentOutput = computed(() =>
    resolveLatestWorkspaceAgentContent({
      agentStreamActive: agentStreamActive.value,
      agentStreamMessageId: agentStreamMessageId.value,
      ideThreadMessages: currentWorkspaceIdeThreadMessages.value,
      operatorThreadMessages: operatorThreadMessages.value,
    }),
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
    ...draftDocuments.value,
    ...dtoDocuments.value,
  ]);
  const activeEditorDocument = computed(() => {
    const matched = editorDocuments.value.find(
      (document) => document.id === activeEditorDocumentId.value,
    );
    if (matched) {
      return matched;
    }

    const selectedPath = filePathFromDocumentId(activeEditorDocumentId.value);
    if (selectedPath) {
      const loadState = fileContentLoadStates.value[selectedPath] ?? 'idle';
      return {
        id: activeEditorDocumentId.value,
        title: selectedPath,
        language: languageForFilePath(selectedPath) as EditorDocumentLanguage,
        value: fileContents.value[selectedPath] ?? '',
        description:
          loadState === 'loaded'
            ? 'Workspace file on disk.'
            : 'Loading workspace file…',
        source: 'file' as const,
        filePath: selectedPath,
        readOnly: loadState !== 'loaded',
        dirty: false,
      };
    }

    if (fileDocuments.value.length > 0) {
      return fileDocuments.value[0];
    }

    return editorDocuments.value[0] ?? null;
  });

  const canSubmitOperatorCommand = computed(
    () =>
      commandMutationState.value !== 'submitting' &&
      !agentStreamActive.value &&
      canSubmitOperatorCommandDraft(
        operatorCommandDraft.value,
        currentWorkspace.value?.workspace_id ?? null,
      ),
  );

  const canSubmitIdeComposer = computed(
    () =>
      commandMutationState.value !== 'submitting' &&
      ideComposerDraft.value.trim().length > 0 &&
      Boolean(currentWorkspace.value?.workspace_id),
  );

  const ideComposerQueue = computed(() => {
    const workspaceId = currentWorkspace.value?.workspace_id;
    if (!workspaceId) {
      return [];
    }
    return ideComposerQueueByWorkspaceId.value[workspaceId] ?? [];
  });

  const ideComposerQueueSummary = computed(() =>
    buildIdeComposerQueueLabel(ideComposerQueue.value.length),
  );

  const composerAgentBusy = computed(
    () => agentStreamActive.value || canStopIdeAgentRun.value,
  );

  const commandSeamHint = computed(() =>
    buildCommandSeamHint(currentWorkspace.value?.workspace_id ?? null),
  );

  const kairoPresenceState = computed<KairoPresenceState>(() => {
    if (kairoVoicePaused.value) {
      return 'paused';
    }
    if (kairoSpeechActive.value || kairoConversationPhase.value === 'speaking') {
      return 'speaking';
    }
    if (kairoConversationPhase.value === 'listening') {
      return 'listening';
    }
    if (kairoConversationPhase.value === 'thinking') {
      return 'thinking';
    }
    if (agentStreamActive.value && ideComposerActivity.value?.mode === 'agent') {
      return kairoSpeechActive.value ? 'speaking' : 'thinking';
    }
    if (agentStreamActive.value) {
      return kairoSpeechActive.value ? 'speaking' : 'thinking';
    }
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

  const kairoAgentLiveLine = computed(() => {
    if (!agentStreamActive.value) {
      return null;
    }
    return ideComposerActivity.value?.label ?? null;
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

  idePresenceProfile = computed<IdePresenceProfile>(() => {
    const summary = runtimeSummary.value;
    return resolveIdePresenceProfile({
      pendingApprovals: pendingApprovalsCount.value,
      criticalSignals: summary?.signals.critical_count ?? 0,
      highSignals: summary?.signals.high_count ?? 0,
      watchConnected: Boolean(summary?.watch.connected),
      degradedActive: Boolean(summary?.degraded.active),
      primaryRunPhase: primaryActiveRun.value?.phase,
      agentStreamActive: agentStreamActive.value,
      voiceSessionActive:
        kairoSpeechActive.value ||
        kairoConversationPhase.value !== 'idle' ||
        agentStreamActive.value,
    });
  });

  const kairoSpeechActive = computed(
    () =>
      kairoSpeechQueueActive.value ||
      kairoVoiceEngineActive.value ||
      kairoConversationPhase.value === 'speaking' ||
      kairoVoicePaused.value,
  );

  const ideDisplayKairoPresenceState = computed<KairoPresenceState>(() =>
    layoutMode.value === 'ide'
      ? ideDisplayKairoState(idePresenceProfile.value, kairoPresenceState.value)
      : kairoPresenceState.value,
  );

  const effectiveKairoNarrationLevel = computed(() =>
    effectiveKairoNarration({
      settingsNarration: operatorPresenceSettings.value.kairo_narration ?? 'minimal',
      layoutMode: layoutMode.value,
      idePresenceProfile: idePresenceProfile.value,
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
  const {
    applyOperatorDockDefaults,
    dockSeamState,
    setDockHeroMode,
    setLeftSidebarMode,
    toggleDockHeroMode,
    toggleDockSeam,
  } = createDockLayoutSlice({
    layoutMode,
    dockSeamLayout,
    expandedDockSeams,
    dockThreadSeamTouched,
    pendingApprovalsCount,
    operatorBriefing,
    runtimeSummary,
    inboxItems,
    leftSidebarMode,
    leftSidebarModeTouched,
    dockHeroMode,
    dockHeroModeTouched,
    briefingSeamEmphasized,
  });

  function getWorkspaceStreamUi(workspaceId: string): WorkspaceStreamUiState {
    return workspaceStreamUiById.value[workspaceId] ?? defaultWorkspaceStreamUi();
  }

  function applyWorkspaceStreamUiToGlobals(workspaceId: string): void {
    if (!shouldSyncWorkspaceStreamGlobals(currentWorkspace.value?.workspace_id, workspaceId)) {
      return;
    }
    const next = getWorkspaceStreamUi(workspaceId);
    const globals = workspaceStreamGlobalsFromState(next);
    agentStreamActive.value = globals.agentStreamActive;
    agentStreamMessageId.value = globals.agentStreamMessageId;
    ideComposerActivity.value = globals.ideComposerActivity as IdeComposerActivity | null;
    ideAgentRunId.value = globals.ideAgentRunId;
  }

  function setWorkspaceStreamUi(
    workspaceId: string,
    partial: Partial<WorkspaceStreamUiState>,
  ): void {
    workspaceStreamUiById.value = {
      ...workspaceStreamUiById.value,
      [workspaceId]: {
        ...getWorkspaceStreamUi(workspaceId),
        ...partial,
      },
    };
    applyWorkspaceStreamUiToGlobals(workspaceId);
  }

  function stashWorkspaceIdeView(workspaceId: string): void {
    workspaceIdeThreadMessagesById.value = {
      ...workspaceIdeThreadMessagesById.value,
      [workspaceId]: [...threadMessages.value],
    };
    setWorkspaceStreamUi(workspaceId, {
      active: agentStreamActive.value,
      messageId: agentStreamMessageId.value,
      activity: ideComposerActivity.value,
      ideAgentRunId: ideAgentRunId.value,
    });
    if (activeThreadId.value) {
      setWorkspaceSurfaceThreadId(workspaceId, currentThreadSurface(), activeThreadId.value);
    }
  }

  async function restoreWorkspaceIdeView(workspaceId: string): Promise<void> {
    const streamUi = getWorkspaceStreamUi(workspaceId);
    agentStreamActive.value = streamUi.active;
    agentStreamMessageId.value = streamUi.messageId;
    ideComposerActivity.value = streamUi.activity;
    ideAgentRunId.value = streamUi.ideAgentRunId;

    const cached = workspaceIdeThreadMessagesById.value[workspaceId];
    if (cached?.length) {
      if (isViewingWorkspaceSurface(workspaceId, 'ide')) {
        threadMessages.value = cached;
        activeThreadId.value = getWorkspaceSurfaceThreadId(workspaceId, 'ide');
        commandMutationState.value = 'idle';
        commandMutationError.value = null;
      }
      await loadIdeThreads(workspaceId);
      return;
    }

    await loadIdeThreads(workspaceId);
    bootstrapIdeActiveThreadId(workspaceId);
    await loadWorkspaceThread(
      workspaceId,
      'ide',
      getWorkspaceSurfaceThreadId(workspaceId, 'ide'),
    );
    applyIdeThreadMessagesToView(workspaceId);
  }

  function resetThreadContext(): void {
    const workspaceId = currentWorkspace.value?.workspace_id;
    if (workspaceId) {
      disconnectChatStreamSession(workspaceId);
      setWorkspaceStreamUi(workspaceId, {
        active: false,
        messageId: null,
        activity: null,
      });
      const nextThreadCache = { ...workspaceIdeThreadMessagesById.value };
      delete nextThreadCache[workspaceId];
      workspaceIdeThreadMessagesById.value = nextThreadCache;
    } else {
      disconnectAllChatStreamSessions();
    }
    agentStreamActive.value = false;
    agentStreamMessageId.value = null;
    agentReportEditorLinksByMessageId.value = {};
    threadMessages.value = [];
    activeThreadId.value = null;
    operatorCommandDraft.value = '';
    commandMutationState.value = 'idle';
    commandMutationError.value = null;
  }

  async function refreshThreadHistory(threadId: string): Promise<void> {
    const history = await fetchThreadHistory(threadId);
    activeThreadId.value = history.thread_id;
    threadMessages.value = history.items.map((item) => mapChatMessageRecord(item));
  }

  const {
    currentThreadSurface,
    isViewingWorkspaceSurface,
    getWorkspaceSurfaceThreadId,
    setWorkspaceSurfaceThreadId,
    clearWorkspaceSurfaceThreadId,
  } = createThreadSurfaceSlice({
    layoutMode,
    currentWorkspace,
    workspaceSurfaceThreadIds,
  });

  const activeIdeThreadId = computed(() => {
    const workspaceId = currentWorkspace.value?.workspace_id;
    if (!workspaceId) {
      return null;
    }
    return getWorkspaceSurfaceThreadId(workspaceId, 'ide');
  });

  const ideThreadsForCurrentWorkspace = computed(() => {
    const workspaceId = currentWorkspace.value?.workspace_id;
    if (!workspaceId) {
      return [];
    }
    return sortIdeThreadsNewestFirst(ideThreadsByWorkspaceId.value[workspaceId] ?? []);
  });

  const openIdeThreadTabsForCurrentWorkspace = computed(() => {
    const workspaceId = currentWorkspace.value?.workspace_id;
    if (!workspaceId) {
      return [];
    }
    return resolveOpenIdeThreadTabItems({
      openIds: openIdeThreadIdsByWorkspaceId.value[workspaceId] ?? [],
      threads: ideThreadsByWorkspaceId.value[workspaceId] ?? [],
      activeThreadId: getWorkspaceSurfaceThreadId(workspaceId, 'ide'),
      workspaceId,
    });
  });

  function persistOpenIdeThreadTabs(workspaceId: string, threadIds: string[]): void {
    openIdeThreadIdsByWorkspaceId.value = {
      ...openIdeThreadIdsByWorkspaceId.value,
      [workspaceId]: threadIds,
    };
    writeOpenIdeThreadIdsForWorkspace(workspaceId, threadIds);
  }

  function syncOpenIdeThreadTabs(workspaceId: string): void {
    const threads = ideThreadsByWorkspaceId.value[workspaceId] ?? [];
    const knownIds = threads.map((thread) => thread.thread_id);
    const activeId = getWorkspaceSurfaceThreadId(workspaceId, 'ide');
    const currentOpen = openIdeThreadIdsByWorkspaceId.value[workspaceId] ?? [];
    const pruned = pruneOpenIdeThreadTabs(currentOpen, knownIds);
    const next = ensureOpenIdeThreadTabs(
      activeId ? openIdeThreadTab(pruned, activeId) : pruned,
      activeId,
    );
    if (next.join('|') !== currentOpen.join('|')) {
      persistOpenIdeThreadTabs(workspaceId, next);
    }
  }

  function ensureIdeThreadTabOpen(threadId: string): void {
    const workspaceId = currentWorkspace.value?.workspace_id;
    if (!workspaceId) {
      return;
    }
    const currentOpen = openIdeThreadIdsByWorkspaceId.value[workspaceId] ?? [];
    const next = openIdeThreadTab(currentOpen, threadId);
    if (next.join('|') !== currentOpen.join('|')) {
      persistOpenIdeThreadTabs(workspaceId, next);
    }
  }

  async function closeIdeThreadTab(threadId: string): Promise<void> {
    const workspaceId = currentWorkspace.value?.workspace_id;
    if (!workspaceId) {
      return;
    }

    const currentOpen = openIdeThreadIdsByWorkspaceId.value[workspaceId] ?? [];
    if (currentOpen.length <= 1) {
      return;
    }

    const nextOpen = currentOpen.filter((id) => id !== threadId);
    persistOpenIdeThreadTabs(workspaceId, nextOpen);

    const nextActive = resolveIdeThreadTabAfterClose({
      openIds: currentOpen,
      closedId: threadId,
      activeId: activeIdeThreadId.value,
    });
    if (nextActive && nextActive !== activeIdeThreadId.value) {
      await selectIdeThread(nextActive);
    }
  }

  const workspaceThreadLoadQueue = createWorkspaceThreadLoadQueue();
  const ideThreadsLoadPromises = new Map<string, Promise<void>>();

  function bootstrapIdeActiveThreadId(workspaceId: string): string | null {
    const resolved = resolveBootstrapIdeThreadId({
      selectedThreadId: getWorkspaceSurfaceThreadId(workspaceId, 'ide'),
      openTabIds: openIdeThreadIdsByWorkspaceId.value[workspaceId] ?? [],
      threadListIds: (ideThreadsByWorkspaceId.value[workspaceId] ?? []).map(
        (thread) => thread.thread_id,
      ),
    });
    if (resolved && resolved !== getWorkspaceSurfaceThreadId(workspaceId, 'ide')) {
      setWorkspaceSurfaceThreadId(workspaceId, 'ide', resolved);
    }
    return resolved;
  }

  function applyLoadedWorkspaceThread(
    workspaceId: string,
    surface: ThreadSurface,
    loadedThreadId: string,
    mapped: OperatorThreadEntry[],
  ): void {
    if (!shouldApplyWorkspaceThreadLoad(getWorkspaceSurfaceThreadId(workspaceId, surface), loadedThreadId)) {
      return;
    }
    if (surface === 'ide') {
      workspaceIdeThreadMessagesById.value = {
        ...workspaceIdeThreadMessagesById.value,
        [workspaceId]: mapped,
      };
      if (currentWorkspace.value?.workspace_id === workspaceId) {
        ideAgentRunId.value = resolveIdeAgentLinkedRunIdFromMessages(mapped, runs.value);
        ensureIdeThreadTabOpen(loadedThreadId);
      }
      syncOpenIdeThreadTabs(workspaceId);
    }
    if (isViewingWorkspaceSurface(workspaceId, surface)) {
      activeThreadId.value = loadedThreadId;
      threadMessages.value = mapped;
      commandMutationState.value = 'idle';
      commandMutationError.value = null;
    }
    if (surface === 'operator' && currentWorkspace.value?.workspace_id === workspaceId) {
      operatorThreadMessages.value = mapped;
    }
  }

  function applyIdeThreadMessagesToView(workspaceId: string): void {
    if (!isViewingWorkspaceSurface(workspaceId, 'ide')) {
      return;
    }
    const threadId = getWorkspaceSurfaceThreadId(workspaceId, 'ide');
    const cached = workspaceIdeThreadMessagesById.value[workspaceId];
    if (!threadId || !cached?.length) {
      return;
    }
    activeThreadId.value = threadId;
    threadMessages.value = cached;
    commandMutationState.value = 'idle';
    commandMutationError.value = null;
  }

  async function loadIdeThreadsImpl(workspaceId: string): Promise<void> {
    try {
      const snapshot = await fetchWorkspaceChatThreads(workspaceId, { surface: 'ide' });
      ideThreadsByWorkspaceId.value = {
        ...ideThreadsByWorkspaceId.value,
        [workspaceId]: snapshot.items,
      };
    } catch {
      ideThreadsByWorkspaceId.value = {
        ...ideThreadsByWorkspaceId.value,
        [workspaceId]: [],
      };
    }
    syncOpenIdeThreadTabs(workspaceId);
  }

  async function loadIdeThreads(workspaceId: string): Promise<void> {
    const inflight = ideThreadsLoadPromises.get(workspaceId);
    if (inflight) {
      return inflight;
    }

    const promise = loadIdeThreadsImpl(workspaceId).finally(() => {
      ideThreadsLoadPromises.delete(workspaceId);
    });
    ideThreadsLoadPromises.set(workspaceId, promise);
    return promise;
  }

  async function hydrateWorkspaceIdeChat(workspaceId: string): Promise<void> {
    await loadIdeThreads(workspaceId);
    bootstrapIdeActiveThreadId(workspaceId);
    const threadId = getWorkspaceSurfaceThreadId(workspaceId, 'ide');
    await loadWorkspaceThread(workspaceId, 'ide', threadId);
    applyIdeThreadMessagesToView(workspaceId);
  }

  async function createIdeThread(): Promise<string | null> {
    const workspaceId = currentWorkspace.value?.workspace_id;
    if (!workspaceId) {
      return null;
    }

    try {
      const created = await createWorkspaceChatThread(workspaceId, { surface: 'ide' });
      ideThreadsByWorkspaceId.value = {
        ...ideThreadsByWorkspaceId.value,
        [workspaceId]: sortIdeThreadsNewestFirst([
          created,
          ...(ideThreadsByWorkspaceId.value[workspaceId] ?? []).filter(
            (thread) => thread.thread_id !== created.thread_id,
          ),
        ]),
      };
      ideComposerDraft.value = '';
      await selectIdeThread(created.thread_id);
      return created.thread_id;
    } catch (error) {
      commandMutationError.value =
        error instanceof Error ? error.message : 'Failed to create a new chat';
      return null;
    }
  }

  async function selectIdeThread(threadId: string): Promise<void> {
    const workspaceId = currentWorkspace.value?.workspace_id;
    if (!workspaceId) {
      return;
    }

    disconnectChatStreamSession(workspaceId);
    setWorkspaceStreamUi(workspaceId, {
      active: false,
      messageId: null,
      activity: null,
      ideAgentRunId: null,
    });

    setWorkspaceSurfaceThreadId(workspaceId, 'ide', threadId);
    activeThreadId.value = threadId;
    ensureIdeThreadTabOpen(threadId);

    if (layoutMode.value === 'ide') {
      threadMessages.value = [];
      ideComposerActivity.value = null;
      ideAgentRunId.value = null;
      commandMutationState.value = 'idle';
      commandMutationError.value = null;
      workspaceIdeThreadMessagesById.value = {
        ...workspaceIdeThreadMessagesById.value,
        [workspaceId]: [],
      };
    }

    await loadWorkspaceThread(workspaceId, 'ide', threadId);
  }

  async function refreshOperatorThreadMessages(workspaceId: string): Promise<void> {
    try {
      const workspaceThread = await fetchWorkspaceChatThread(workspaceId, { surface: 'operator' });
      if (!hasWorkspaceChatThread(workspaceThread)) {
        if (currentWorkspace.value?.workspace_id === workspaceId) {
          operatorThreadMessages.value = [];
        }
        return;
      }
      const history = await fetchThreadHistory(workspaceThread.thread_id);
      const mapped = filterThreadMessagesForSurface(
        history.items.map((item) => mapChatMessageRecord(item)),
        'operator',
      );
      if (currentWorkspace.value?.workspace_id === workspaceId) {
        operatorThreadMessages.value = mapped;
      }
      if (workspaceThread.thread_id) {
        setWorkspaceSurfaceThreadId(workspaceId, 'operator', workspaceThread.thread_id);
      }
    } catch {
      if (currentWorkspace.value?.workspace_id === workspaceId) {
        operatorThreadMessages.value = [];
      }
    }
  }

  async function loadWorkspaceThread(
    workspaceId: string,
    surface: ThreadSurface = currentThreadSurface(),
    requestedThreadId?: string | null,
  ): Promise<void> {
    return workspaceThreadLoadQueue.enqueue(
      workspaceId,
      surface,
      requestedThreadId,
      getWorkspaceSurfaceThreadId(workspaceId, surface),
      () =>
        loadWorkspaceThreadOnce(
          {
            getSelectedThreadId: getWorkspaceSurfaceThreadId,
            setSelectedThreadId: setWorkspaceSurfaceThreadId,
            clearSelectedThreadId: clearWorkspaceSurfaceThreadId,
            isViewingSurface: isViewingWorkspaceSurface,
            isCurrentWorkspace: (id) => currentWorkspace.value?.workspace_id === id,
            applyLoaded: applyLoadedWorkspaceThread,
            resetThreadContext,
            clearIdeAgentRunLink,
            setOperatorThreadEmpty: () => {
              operatorThreadMessages.value = [];
            },
            setLoadError: (message) => {
              commandMutationState.value = 'error';
              commandMutationError.value = message;
            },
            mapChatMessages: (items) => items.map((item) => mapChatMessageRecord(item)),
            filterForSurface: filterThreadMessagesForSurface,
          },
          workspaceId,
          surface,
          requestedThreadId,
        ),
    );
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
        thread_id: getWorkspaceSurfaceThreadId(workspaceId, 'operator'),
        run_id: primaryActiveRun.value?.run_id ?? null,
        composer_mode: 'command',
      });
      activeThreadId.value = response.thread_id;
      setWorkspaceSurfaceThreadId(workspaceId, 'operator', response.thread_id);
      const merged = mergeThreadMessages(
        operatorThreadMessages.value,
        response.messages.map((message) => mapChatMessageRecord(message)),
      );
      operatorThreadMessages.value = filterThreadMessagesForSurface(merged, 'operator');
      if (currentThreadSurface() === 'operator') {
        threadMessages.value = operatorThreadMessages.value;
      }
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

  async function submitOperatorCommandContent(content: string): Promise<void> {
    const trimmed = content.trim();
    if (!trimmed) {
      return;
    }
    operatorCommandDraft.value = trimmed;
    await submitOperatorCommand();
  }

  async function handoffSignalToIde(
    signal: SignalHandoffInput,
    options: { autoSubmit?: boolean } = {},
  ): Promise<void> {
    handoffMutationState.value = 'submitting';
    handoffMutationError.value = null;
    lastDiscussedSignal.value = signal;

    const resolved = resolveSignalHandoff(
      signal,
      currentWorkspace.value?.workspace_id ?? null,
      workspaces.value.map((workspace) => ({
        workspace_id: workspace.workspace_id,
        display_name: workspace.display_name,
      })),
    );
    if (!resolved) {
      handoffMutationState.value = 'error';
      handoffMutationError.value = 'This signal cannot be handed off to the IDE.';
      return;
    }

    try {
      if (resolved.mode === 'handoff' && resolved.sourceWorkspaceId) {
        await createWorkspaceHandoff(resolved.sourceWorkspaceId, {
          target_workspace_id: resolved.targetWorkspaceId,
          task: resolved.task,
          reason: resolved.reason,
        });
      }
      setCurrentWorkspace(resolved.targetWorkspaceId);
      setLayoutMode('ide');
      ideComposerDraft.value = resolved.task;
      await hydrateWorkspaceIdeChat(resolved.targetWorkspaceId);
      if (options.autoSubmit) {
        await submitIdeComposer('agent');
      }
      pendingHandoffDismissSignalId.value = resolved.reason;
      writePendingHandoffDismissSignalId(resolved.reason);
      handoffMutationState.value = 'idle';
    } catch (error) {
      handoffMutationState.value = 'error';
      handoffMutationError.value =
        error instanceof Error ? error.message : 'Failed to hand off signal to IDE';
    }
  }

  async function handoffDiscussedSignalToIde(): Promise<void> {
    if (!lastDiscussedSignal.value) {
      return;
    }
    await handoffSignalToIde(lastDiscussedSignal.value);
  }

  function disconnectChatStreamSession(workspaceId?: string): void {
    if (workspaceId) {
      const session = chatStreamSessionsByWorkspace.get(workspaceId);
      if (session) {
        session.disconnect();
        chatStreamSessionsByWorkspace.delete(workspaceId);
      }
      return;
    }
    disconnectAllChatStreamSessions();
  }

  function disconnectAllChatStreamSessions(): void {
    for (const session of chatStreamSessionsByWorkspace.values()) {
      session.disconnect();
    }
    chatStreamSessionsByWorkspace.clear();
  }

  function patchThreadMessageContent(
    workspaceId: string,
    messageId: string,
    content: string,
    attachments?: OperatorThreadEntry['attachments'],
  ): void {
    const updateMessages = (messages: OperatorThreadEntry[]) =>
      messages.map((message) => {
        if (message.message_id !== messageId) {
          return message;
        }
        const next: OperatorThreadEntry = { ...message, content };
        if (attachments?.length) {
          next.attachments = attachments;
        }
        return next;
      });

    if (currentWorkspace.value?.workspace_id === workspaceId) {
      threadMessages.value = updateMessages(threadMessages.value);
    }

    const cached = workspaceIdeThreadMessagesById.value[workspaceId];
    if (cached) {
      workspaceIdeThreadMessagesById.value = {
        ...workspaceIdeThreadMessagesById.value,
        [workspaceId]: updateMessages(cached),
      };
    }
  }

  function kairoSpeechSessionId(): string {
    const workspaceId = currentWorkspace.value?.workspace_id ?? '';
    const threadId = workspaceId
      ? getWorkspaceSurfaceThreadId(workspaceId, currentThreadSurface())
      : null;
    return buildKairoSpeechSessionId(workspaceId, threadId);
  }

  function voiceDeliveryAllowed(): boolean {
    return ideVoiceSpeechAllowed({
      layoutMode: layoutMode.value,
      settings: operatorPresenceSettings.value,
    });
  }

  function stopKairoSpeech(): void {
    flushKairoSpeechQueue('stopped');
    stopKairoPlayback();
    kairoVoicePaused.value = false;
    if (kairoConversationPhase.value === 'speaking') {
      setKairoConversationPhase('idle');
    }
  }

  function pauseKairoSpeech(): boolean {
    const paused = pauseKairoPlayback();
    kairoVoicePaused.value = paused;
    return paused;
  }

  function resumeKairoSpeech(): boolean {
    const resumed = resumeKairoPlayback();
    if (resumed) {
      kairoVoicePaused.value = false;
      if (kairoConversationPhase.value === 'idle') {
        setKairoConversationPhase('speaking');
      }
    }
    return resumed;
  }

  function interruptKairoVoice(): void {
    void interruptKairoSpeechQueue('barge_in');
    kairoVoicePaused.value = false;
    if (kairoConversationPhase.value === 'speaking') {
      setKairoConversationPhase('idle');
    }
  }

  async function speakKairoConversationLine(
    line: string,
    options?: { operatorPrompt?: string; skipSpeakApi?: boolean },
  ): Promise<void> {
    const trimmed = line.trim();
    const configuredNarration = operatorPresenceSettings.value.kairo_narration ?? 'minimal';
    if (
      !trimmed ||
      !voiceDeliveryAllowed() ||
      operatorPresenceSettings.value.privacy_mode ||
      configuredNarration === 'off'
    ) {
      if (kairoConversationPhase.value === 'thinking') {
        setKairoConversationPhase('idle');
      }
      return;
    }

    setKairoConversationPhase('speaking');
    kairoVoicePaused.value = false;
    let message = trimmed;
    const narration = configuredNarration;
    const operatorPrompt = options?.operatorPrompt?.trim() ?? '';
    const skipSpeakApi = options?.skipSpeakApi === true;

    if (!skipSpeakApi) {
      try {
        const response = await postKairoSpeak({
          event_type: 'conversation_reply',
          context: {
            fallback: trimmed,
            reply: trimmed,
            operator_prompt: operatorPrompt,
            pending_approvals: pendingApprovalsCount.value,
            top_signal_title: operatorBriefing.value?.top_signals[0]?.title ?? '',
            active_run_count: operatorBriefing.value?.active_runs.length ?? 0,
            degraded_active: operatorBriefing.value?.degraded.active ?? false,
          },
          session_id: kairoSpeechSessionId(),
          workspace_id: currentWorkspace.value?.workspace_id ?? '',
          narration,
          use_runtime: narration === 'conversational',
        });
        if (response.line?.trim()) {
          message = response.line.trim();
        }
      } catch {
        // Fall back to the raw reply when the speak endpoint is unavailable.
      }
    }

    await speakKairoLine(message, {
      priority: 'conversation',
    });
  }

  function handleKairoPresenceAction(): void {
    const target = resolveKairoPresenceClickTarget({
      paused: kairoVoicePaused.value,
      voiceBusy:
        kairoSpeechQueueActive.value ||
        kairoVoiceEngineActive.value ||
        isKairoSpeechQueueBusy() ||
        kairoConversationPhase.value === 'speaking' ||
        kairoConversationPhase.value === 'thinking',
      layoutMode: layoutMode.value,
      state: kairoPresenceState.value,
    });
    if (target === 'resume') {
      resumeKairoSpeech();
      return;
    }
    if (target === 'pause') {
      pauseKairoSpeech();
      return;
    }
    if (target === 'interrupt') {
      interruptKairoVoice();
      setKairoConversationPhase('idle');
      return;
    }
    if (target === 'attention') {
      focusAttentionSidebar();
      return;
    }
    focusKairoBriefing();
  }

  if (typeof window !== 'undefined') {
    subscribeSpeechQueueSpeaking((active) => {
      kairoSpeechQueueActive.value = active;
    });
    subscribeKairoVoiceSpeaking((active) => {
      kairoVoiceEngineActive.value = active;
    });
    const finishKairoSpeechPhase = (): void => {
      kairoVoicePaused.value = false;
      if (kairoConversationPhase.value === 'speaking' && !isKairoVoiceSpeaking()) {
        setKairoConversationPhase('idle');
      }
    };
    onSpeechQueueIdle(finishKairoSpeechPhase);
    onKairoVoiceIdle(finishKairoSpeechPhase);
  }

  async function deliverKairoSpokenAlert(alert: SpokenAlertEligibility): Promise<void> {
    if (!voiceDeliveryAllowed()) {
      return;
    }
    if (!alert.eligible || !operatorPresenceSettings.value.spoken_alerts_enabled) {
      return;
    }
    if (operatorPresenceSettings.value.privacy_mode) {
      return;
    }
    if (effectiveKairoNarrationLevel.value === 'off') {
      return;
    }

    let eventType = 'alert';
    const topSignal = operatorBriefing.value?.top_signals[0];
    const context: Record<string, unknown> = {
      fallback: alert.message,
      pending_approvals: pendingApprovalsCount.value,
      top_signal_title: topSignal?.title ?? '',
      top_signal_workspace_id: topSignal?.workspace_id ?? '',
      top_signal_summary: topSignal?.summary ?? '',
      degraded_active: Boolean(runtimeSummary.value?.degraded.active),
    };

    if (alert.reason === 'operator_approval_required') {
      eventType = 'approval_literal';
      context.literal_line = alert.message.replace(/^(?:VAXON|NAXON|X|KAIRO):\s*/i, '').trim();
    }

    let message = '';
    try {
      const response = await postKairoSpeak({
        event_type: eventType,
        context,
        session_id: kairoSpeechSessionId(),
        workspace_id: currentWorkspace.value?.workspace_id ?? '',
        narration: effectiveKairoNarrationLevel.value,
      });
      if (response.source === 'skipped' || !response.line?.trim()) {
        return;
      }
      message = response.line.trim();
    } catch {
      return;
    }

    void deliverSpokenOperatorAlert({
      eligible: true,
      reason: alert.reason,
      signal_id: alert.signal_id,
      message,
    });
  }

  async function speakOperatorBriefing(): Promise<void> {
    if (!voiceDeliveryAllowed() || operatorPresenceSettings.value.privacy_mode) {
      return;
    }
    if (effectiveKairoNarrationLevel.value === 'off') {
      return;
    }

    const notice = operatorBriefing.value?.notice?.trim() ?? '';
    const advise = operatorBriefing.value?.advise?.trim() ?? '';
    if (!notice && !advise) {
      return;
    }

    try {
      const response = await postKairoSpeak({
        event_type: 'briefing',
        context: {
          notice,
          advise,
          workspace_id: currentWorkspace.value?.workspace_id ?? '',
          pending_approvals: pendingApprovalsCount.value,
          top_signal_title: operatorBriefing.value?.top_signals[0]?.title ?? '',
        },
        session_id: kairoSpeechSessionId(),
        workspace_id: currentWorkspace.value?.workspace_id ?? '',
        narration: effectiveKairoNarrationLevel.value,
        use_runtime: true,
      });
      if (response.source === 'skipped' || !response.line?.trim()) {
        return;
      }
      const channel = await deliverSpokenOperatorAlert({
        eligible: true,
        reason: 'operator_briefing_spoken',
        signal_id: null,
        message: response.line.trim(),
      }, sessionStorage, { dedupe: false });
      if (channel !== 'skipped') {
        briefingVoiceTranscript.value = appendBriefingVoiceTranscriptEntry({
          message: response.line.trim(),
          workspaceId: currentWorkspace.value?.workspace_id ?? null,
        });
      }
      scheduleBriefingSurfaceOffer();
    } catch {
      // Voice line unavailable — operator can read briefing in dock.
    }
  }

  async function maybeSpeakBootGreeting(): Promise<void> {
    if (!voiceDeliveryAllowed()) {
      return;
    }
    const greetingKey = 'axon-x:kairo-greeting-spoken';
    if (typeof sessionStorage !== 'undefined' && sessionStorage.getItem(greetingKey) === '1') {
      return;
    }
    if (effectiveKairoNarrationLevel.value === 'off' || operatorPresenceSettings.value.privacy_mode) {
      return;
    }

    let message = '';
    try {
      const response = await postKairoSpeak({
        event_type: 'greeting',
        context: {
          workspace_count: workspaces.value.length,
          pending_approvals: pendingApprovalsCount.value,
        },
        session_id: kairoSpeechSessionId(),
        workspace_id: currentWorkspace.value?.workspace_id ?? '',
        narration: effectiveKairoNarrationLevel.value,
      });
      if (response.source === 'skipped' || !response.line?.trim()) {
        return;
      }
      message = response.line.trim();
    } catch {
      return;
    }

    if (typeof sessionStorage !== 'undefined') {
      sessionStorage.setItem(greetingKey, '1');
    }

    void deliverSpokenOperatorAlert({
      eligible: true,
      reason: 'boot_greeting',
      signal_id: null,
      message,
    });
  }

  function kairoVoiceContext(): {
    fullAccess: boolean;
    activeFile?: string | null;
  } {
    return {
      fullAccess: ideComposerActivity.value?.executionAccess === 'full',
      activeFile: activeWorkspaceFilePath.value,
    };
  }

  function attachChatStream(workspaceId: string, threadId: string, messageId: string): void {
    disconnectChatStreamSession(workspaceId);
    setWorkspaceStreamUi(workspaceId, {
      active: true,
      messageId,
      activity: ideComposerActivity.value,
      ideAgentRunId: ideAgentRunId.value,
    });
    workspaceIdeThreadMessagesById.value = {
      ...workspaceIdeThreadMessagesById.value,
      [workspaceId]: [...threadMessages.value],
    };
    const narrationEnabled = ideComposerActivity.value?.mode === 'agent';
    const fullAccessNarration = ideComposerActivity.value?.executionAccess === 'full';
    const operatorPrompt = ideComposerActivity.value?.operatorPrompt?.trim() ?? '';
    let streamedContent = '';
    let spokenStartIntent = false;
    const streamIncremental = createAgentStreamIncrementalState();
    const streamUiBatcher = createRafStreamUiBatcher<Partial<WorkspaceStreamUiState>>(
      (wsId, partial) => setWorkspaceStreamUi(wsId, partial),
    );
    const voiceContext = kairoVoiceContext();
    const progressNarrator = narrationEnabled
      ? createKairoProgressNarrator({
          messageId,
          sessionId: kairoSpeechSessionId,
          workspaceId: () => workspaceId,
          narration: () => effectiveKairoNarrationLevel.value,
          voiceDeliveryAllowed,
        })
      : null;
    const agentMilestoneNarrator = narrationEnabled
      ? createKairoAgentMilestoneNarrator({
          messageId,
          sessionId: kairoSpeechSessionId,
          workspaceId: () => workspaceId,
          narration: () => effectiveKairoNarrationLevel.value,
          voiceDeliveryAllowed,
          operatorPrompt: () => operatorPrompt,
          fullAccess: () => voiceContext.fullAccess,
        })
      : null;

    chatStreamSessionsByWorkspace.set(
      workspaceId,
      startChatStreamSession({
        threadId,
        messageId,
        onDelta: (content) => {
          streamedContent = content;
          patchThreadMessageContent(workspaceId, messageId, content);
          for (const milestone of streamIncremental.consumeFullContent(content)) {
            if (narrationEnabled) {
              agentMilestoneNarrator?.narrate(milestone);
            }
          }
          const activity = getWorkspaceStreamUi(workspaceId).activity as IdeComposerActivity | null;
          if (activity) {
            const activityView = streamIncremental.toStreamingActivityView(fullAccessNarration);
            const nextActivity: IdeComposerActivity = {
              ...activity,
              label: activityView.label,
              liveBodyFull: activityView.liveBodyFull,
              liveBodySpoken: activityView.liveBodySpoken,
              liveBodyTruncated: activityView.liveBodyTruncated,
              streamCounts: streamIncremental.toCounts(),
            };
            streamUiBatcher.schedule(workspaceId, { activity: nextActivity });

            const spokenBlock = activityView.liveBodySpoken?.trim() ?? '';
            if (
              narrationEnabled &&
              !spokenStartIntent &&
              spokenBlock &&
              shouldSpeakLiveThinkingBlock({
                narration: effectiveKairoNarrationLevel.value,
                spokenBlock,
              })
            ) {
              spokenStartIntent = true;
              agentMilestoneNarrator?.narrate({
                key: 'start',
                message: spokenBlock,
              });
            }
          }
        },
        onMilestone: (payload) => {
          if (!narrationEnabled || !payload.event_key || !payload.event_type) {
            return;
          }
          progressNarrator?.narrate({
            eventKey: payload.event_key,
            eventType: payload.event_type,
            context: {
              operator_prompt: operatorPrompt,
              ...(payload.context ?? {}),
            },
          });
        },
        onDone: (payload) => {
          if (payload.system_message_id && payload.system_content) {
            patchThreadMessageContent(
              workspaceId,
              payload.system_message_id,
              payload.system_content,
            );
          }
          const streamAttachments = (payload.attachments ?? [])
            .map((item) => ({
              attachment_id: String(item.attachment_id ?? '').trim(),
              filename: String(item.filename ?? '').trim(),
              mime_type: String(item.mime_type ?? '').trim(),
              url: String(item.url ?? '').trim(),
            }))
            .filter((item) => item.attachment_id && item.url);
          if (streamAttachments.length) {
            patchThreadMessageContent(
              workspaceId,
              messageId,
              payload.content ?? streamedContent,
              streamAttachments,
            );
          }
          const uiAction = parseChatUiAction(payload.ui_action);
          if (uiAction) {
            applyChatUiAction(
              {
                setCurrentWorkspace,
                openWorkspaceFile,
                setLayoutMode,
              },
              uiAction,
            );
          }
          const finalContent = payload.content ?? streamedContent;
          if (narrationEnabled) {
            agentMilestoneNarrator?.narrate(narrationForCompletion(finalContent));
          }
          if (currentWorkspace.value?.workspace_id === workspaceId) {
            for (const path of editedFilePathsFromTranscript(finalContent)) {
              if (openedFilePaths.value.includes(path)) {
                void reloadWorkspaceFile(path);
              }
            }
          }
          streamUiBatcher.flushNow(workspaceId);
          setWorkspaceStreamUi(workspaceId, {
            active: false,
            messageId: null,
            activity: null,
            ideAgentRunId: null,
          });
          streamUiBatcher.cancel(workspaceId);
          disconnectChatStreamSession(workspaceId);
          void refreshRunSurfaces().finally(() => {
            void flushIdeComposerQueueIfIdle();
          });
        },
        onError: (message, payload) => {
          if (narrationEnabled) {
            const errorSummary = message.trim().slice(0, 120);
            const failureContent = streamedContent || message;
            const completion = narrationForCompletion(failureContent);
            agentMilestoneNarrator?.narrate(
              completion.key === 'failed'
                ? { ...completion, message: errorSummary || completion.message }
                : { key: 'failed', message: errorSummary || 'Failed' },
            );
          }
          if (payload?.system_message_id && payload.system_content) {
            patchThreadMessageContent(
              workspaceId,
              payload.system_message_id,
              payload.system_content,
            );
          }
          if (currentWorkspace.value?.workspace_id === workspaceId) {
            commandMutationError.value = message;
          }
          streamUiBatcher.flushNow(workspaceId);
          setWorkspaceStreamUi(workspaceId, {
            active: false,
            messageId: null,
            activity: null,
          });
          streamUiBatcher.cancel(workspaceId);
          disconnectChatStreamSession(workspaceId);
          void refreshRunSurfaces().finally(() => {
            void flushIdeComposerQueueIfIdle();
          });
        },
      }),
    );
  }

  function clearIdeAgentRunLink(): void {
    ideAgentRunId.value = null;
  }

  function restoreComposerDraft(content: string): void {
    const trimmed = content.trim();
    commandMutationError.value = null;
    if (layoutMode.value === 'operator') {
      operatorCommandDraft.value = trimmed;
      setDockHeroMode('command');
      commandFocusToken.value += 1;
      return;
    }
    ideComposerDraft.value = trimmed;
    agentDockCollapsed.value = false;
    persistAgentDockCollapsed(false);
    ideActivityView.value = 'agent';
    commandFocusToken.value += 1;
  }

  function syncIdeComposerDraftForWorkspace(workspaceId: string | null | undefined): void {
    ideComposerDraft.value = readStoredIdeComposerDraft(workspaceId);
  }

  function schedulePersistIdeComposerDraft(): void {
    if (typeof window === 'undefined') {
      return;
    }
    if (ideComposerDraftPersistTimer) {
      clearTimeout(ideComposerDraftPersistTimer);
    }
    ideComposerDraftPersistTimer = setTimeout(() => {
      ideComposerDraftPersistTimer = null;
      persistIdeComposerDraft(
        currentWorkspace.value?.workspace_id ?? null,
        ideComposerDraft.value,
      );
    }, 140);
  }

  watch(ideComposerDraft, () => {
    schedulePersistIdeComposerDraft();
  });

  function latestIdeOperatorPromptForRun(runId: string | null | undefined): string | null {
    const targetRunId = String(runId ?? '').trim();
    const messages = [...threadMessages.value].reverse();
    if (targetRunId) {
      const linked = messages.find(
        (message) =>
          message.role === 'operator' &&
          String(message.run_id ?? '').trim() === targetRunId &&
          message.content.trim(),
      );
      if (linked) {
        return linked.content.trim();
      }
    }
    const fallback = messages.find(
      (message) => message.role === 'operator' && message.content.trim(),
    );
    return fallback?.content.trim() ?? null;
  }

  async function dispatchIdeComposerMessage(
    composerMode: 'ask' | 'plan' | 'agent',
    options: {
      contentOverride?: string;
      linkedRunIdOverride?: string | null;
      clearDraftOnSuccess?: boolean;
      attachmentFiles?: File[];
    } = {},
  ): Promise<boolean> {
    const workspaceId = currentWorkspace.value?.workspace_id ?? null;
    const content = (options.contentOverride ?? ideComposerDraft.value).trim();
    if (
      commandMutationState.value === 'submitting' ||
      agentStreamActive.value ||
      !workspaceId ||
      !content
    ) {
      return false;
    }

    commandMutationState.value = 'submitting';
    commandMutationError.value = null;
    ideComposerActivity.value = {
      label: buildIdeComposerActivityLabel(composerMode, agentExecutionAccess.value),
      mode: composerMode,
      executionAccess: agentExecutionAccess.value,
      operatorPrompt: content,
    };

    try {
      const linkedRunId =
        composerMode === 'agent'
          ? options.linkedRunIdOverride ?? resolveIdeAgentLinkedRunId(ideAgentRunId.value, runs.value)
          : null;
      const contextPayload = resolveComposerContextPayload({
        draft: content,
        workspaceId,
        activeFilePath: activeWorkspaceFilePath.value,
        terminalSessionId: activeTerminalSessionId.value,
        editorSelection: editorSelection.value
          ? {
              startLine: editorSelection.value.startLine,
              endLine: editorSelection.value.endLine,
              text: editorSelection.value.text,
            }
          : null,
      });
      const attachmentIds: string[] = [];
      for (const file of options.attachmentFiles ?? []) {
        const uploaded = await uploadChatAttachment(workspaceId, file);
        attachmentIds.push(uploaded.attachment_id);
      }
      const response = await postChatMessage({
        workspace_id: workspaceId,
        content,
        thread_id: getWorkspaceSurfaceThreadId(workspaceId, 'ide'),
        run_id: linkedRunId,
        composer_mode: composerMode,
        active_file_path: activeWorkspaceFilePath.value,
        editor_selection: contextPayload.editor_selection,
        terminal_snippet: contextPayload.terminal_snippet,
        attachment_ids: attachmentIds.length ? attachmentIds : undefined,
        runtime_target: selectedRuntimeTargetId.value || null,
        runtime_model: selectedComposerModel.value || null,
        execution_access: composerMode === 'agent' ? agentExecutionAccess.value : undefined,
        kairo_session_id: kairoSpeechSessionId(),
      });
      activeThreadId.value = response.thread_id;
      setWorkspaceSurfaceThreadId(workspaceId, 'ide', response.thread_id);
      void loadIdeThreads(workspaceId);
      const merged = mergeThreadMessages(
        threadMessages.value,
        response.messages.map((message) => mapChatMessageRecord(message)),
      );
      threadMessages.value = filterThreadMessagesForSurface(merged, 'ide');
      if (options.clearDraftOnSuccess !== false) {
        ideComposerDraft.value = '';
      }
      if (composerMode === 'agent' && response.run_id) {
        ideAgentRunId.value = response.run_id;
      }
      const uiAction = parseChatUiAction(response.ui_action);
      if (uiAction) {
        applyChatUiAction(
          {
            setCurrentWorkspace,
            openWorkspaceFile,
          },
          uiAction,
        );
      }
      if (response.streaming && response.stream_agent_message_id) {
        commandMutationState.value = 'idle';
        if (response.agent_terminal_session) {
          applyAgentTerminalSession(response.agent_terminal_session);
          revealIdeTerminalPanel();
        }
        ideComposerActivity.value = {
          label: buildIdeStreamActivityLabel(agentExecutionAccess.value),
          mode: composerMode,
          executionAccess: agentExecutionAccess.value,
          operatorPrompt: content,
        };
        attachChatStream(workspaceId, response.thread_id, response.stream_agent_message_id);
        const next = new Set(expandedDockSeams.value);
        next.add('thread');
        if (response.run_id) {
          next.add('run');
        }
        expandedDockSeams.value = next;
        return true;
      }
      commandMutationState.value = 'idle';
      if (response.run || response.run_id) {
        await refreshRunSurfaces();
        const next = new Set(expandedDockSeams.value);
        next.add('run');
        next.add('thread');
        expandedDockSeams.value = next;
      } else if (response.dispatched) {
        await refreshRunSurfaces();
        const next = new Set(expandedDockSeams.value);
        next.add('thread');
        expandedDockSeams.value = next;
      } else {
        const next = new Set(expandedDockSeams.value);
        next.add('thread');
        expandedDockSeams.value = next;
      }
      return true;
    } catch (error) {
      commandMutationState.value = 'error';
      commandMutationError.value =
        error instanceof Error ? error.message : 'Failed to submit IDE composer message';
      return false;
    } finally {
      if (!agentStreamActive.value) {
        ideComposerActivity.value = null;
      }
    }
  }

  function setAgentExecutionAccess(value: AgentExecutionAccess): void {
    const normalized = normalizeAgentExecutionAccess(value);
    if (normalized === 'full') {
      markFullAccessSessionConsent();
    } else {
      clearFullAccessSessionConsent();
      persistAgentExecutionAccess('consultative');
      agentExecutionAccess.value = 'consultative';
      return;
    }
    agentExecutionAccess.value = normalized;
    persistAgentExecutionAccess(normalized);
  }

  function resolveActiveIdeStopRun(): RunRecord | null {
    return activeIdeStopRun.value;
  }

  function enqueueIdeComposerMessage(
    composerMode: IdeComposerMode,
    content: string,
  ): void {
    const workspaceId = currentWorkspace.value?.workspace_id;
    const trimmed = content.trim();
    if (!workspaceId || !trimmed) {
      return;
    }

    const entry: IdeComposerQueuedMessage = {
      id: `queued_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      content: trimmed,
      composerMode,
      createdAt: new Date().toISOString(),
    };
    ideComposerQueueByWorkspaceId.value = {
      ...ideComposerQueueByWorkspaceId.value,
      [workspaceId]: appendIdeComposerQueueEntry(
        ideComposerQueueByWorkspaceId.value[workspaceId] ?? [],
        entry,
      ),
    };
  }

  function removeIdeComposerQueuedMessage(messageId: string): void {
    const workspaceId = currentWorkspace.value?.workspace_id;
    if (!workspaceId) {
      return;
    }
    ideComposerQueueByWorkspaceId.value = {
      ...ideComposerQueueByWorkspaceId.value,
      [workspaceId]: removeIdeComposerQueueEntry(
        ideComposerQueueByWorkspaceId.value[workspaceId] ?? [],
        messageId,
      ),
    };
  }

  async function flushIdeComposerQueueIfIdle(): Promise<void> {
    if (flushingIdeComposerQueue) {
      return;
    }
    if (composerAgentBusy.value || commandMutationState.value === 'submitting') {
      return;
    }

    const workspaceId = currentWorkspace.value?.workspace_id;
    if (!workspaceId) {
      return;
    }

    const queue = ideComposerQueueByWorkspaceId.value[workspaceId] ?? [];
    const { next, remaining } = shiftIdeComposerQueue(queue);
    if (!next) {
      return;
    }

    flushingIdeComposerQueue = true;
    ideComposerQueueByWorkspaceId.value = {
      ...ideComposerQueueByWorkspaceId.value,
      [workspaceId]: remaining,
    };

    try {
      await dispatchIdeComposerMessage(next.composerMode, {
        contentOverride: next.content,
      });
    } finally {
      flushingIdeComposerQueue = false;
      void flushIdeComposerQueueIfIdle();
    }
  }

  async function steerIdeComposer(
    composerMode: 'ask' | 'plan' | 'agent',
    options: { attachmentFiles?: File[] } = {},
  ): Promise<void> {
    const content = ideComposerDraft.value.trim();
    if (!content || !currentWorkspace.value?.workspace_id) {
      return;
    }

    if (composerAgentBusy.value) {
      await stopIdeAgentRun();
    }

    await dispatchIdeComposerMessage(composerMode, options);
  }

  async function steerQueuedIdeComposerMessage(messageId: string): Promise<void> {
    const workspaceId = currentWorkspace.value?.workspace_id;
    if (!workspaceId) {
      return;
    }

    const queue = ideComposerQueueByWorkspaceId.value[workspaceId] ?? [];
    const entry = queue.find((item) => item.id === messageId);
    if (!entry) {
      return;
    }

    ideComposerQueueByWorkspaceId.value = {
      ...ideComposerQueueByWorkspaceId.value,
      [workspaceId]: removeIdeComposerQueueEntry(queue, messageId),
    };

    if (composerAgentBusy.value) {
      await stopIdeAgentRun();
    }

    await dispatchIdeComposerMessage(entry.composerMode, {
      contentOverride: entry.content,
    });
  }

  async function submitIdeComposer(
    composerMode: 'ask' | 'plan' | 'agent',
    options: { attachmentFiles?: File[] } = {},
  ): Promise<void> {
    const content = ideComposerDraft.value.trim();
    if (!content || !currentWorkspace.value?.workspace_id) {
      return;
    }

    if (
      shouldQueueIdeComposerSubmit({
        agentBusy: composerAgentBusy.value,
        composerMode,
      }) &&
      !(options.attachmentFiles?.length)
    ) {
      enqueueIdeComposerMessage(composerMode, content);
      ideComposerDraft.value = '';
      commandMutationError.value = null;
      return;
    }

    await dispatchIdeComposerMessage(composerMode, options);
  }

  async function runOperatorCommand(content: string): Promise<void> {
    operatorCommandDraft.value = content.trim();
    setDockHeroMode('command');
    commandFocusToken.value += 1;
    await submitOperatorCommand();
  }

  const {
    focusAttentionSidebar,
    closeIdeAttentionPanel,
    closeIdeBriefingPanel,
    openIdeBriefingPanel,
    toggleSignalDetails,
    focusMissionControl,
    setOperatorCenterView,
    afterRunLifecycleMutation,
    focusKairoBriefing,
    focusCommandSeam,
  } = createOperatorFocusSlice({
    layoutMode,
    operatorBriefing,
    highlightedSignalId,
    ideAttentionPanelOpen,
    ideBriefingPanelOpen,
    ideExplorerCollapsed,
    signalsSeamEmphasized,
    missionControlEmphasized,
    briefingSeamEmphasized,
    operatorCenterView,
    dockHeroMode,
    setLeftSidebarMode,
    setDockHeroMode,
    restoreComposerDraft,
  });

  const {
    syncCurrentWorkspace,
    loadWorkspaces,
    loadRuns,
    loadRunHistory,
  } = createCatalogLoadersSlice({
    workspaces,
    currentWorkspace,
    operatorPinnedWorkspaceId,
    workspacesLoadState,
    workspacesError,
    runs,
    activeRun,
    runsLoadState,
    runsError,
    runHistorySnapshot,
    runHistoryLoadState,
  });

  function setLayoutMode(mode: LayoutMode): void {
    layoutMode.value = mode;
    persistLayoutMode(mode);
    ideAttentionPanelOpen.value = false;
    ideBriefingPanelOpen.value = false;
    expandedDockSeams.value = new Set();
    dockHeroModeTouched.value = false;
    leftSidebarModeTouched.value = false;
    applyOperatorDockDefaults();
    const workspaceId = currentWorkspace.value?.workspace_id;
    if (workspaceId) {
      if (mode === 'operator') {
        threadMessages.value = operatorThreadMessages.value;
        void loadWorkspaceThread(workspaceId, 'operator');
      } else {
        void hydrateWorkspaceIdeChat(workspaceId);
      }
    }
    if (mode === 'ide' && workspaceId) {
      if (workspaceFilesLoadState.value === 'idle') {
        workspaceFilesLoadState.value = 'loading';
      }
      void loadWorkspaceFiles();
    }
  }

  const {
    revealIdeTerminalPanel,
    toggleIdeTerminalPanel,
    setIdeActivityView,
    toggleIdeExplorer,
    toggleAgentDock,
  } = createIdeWorkbenchChromeSlice({
    ideTerminalRevealToken,
    ideTerminalToggleToken,
    ideActivityView,
    ideExplorerCollapsed,
    agentDockCollapsed,
    ideAttentionPanelOpen,
    ideBriefingPanelOpen,
  });

  const terminalSessionStore = createTerminalSessionStore({
    currentWorkspace,
    terminalSessions,
    activeTerminalSessionId,
    ideAgentRunId,
    revealIdeTerminalPanel,
  });
  const {
    activeTerminalSession,
    applyAgentTerminalSession,
    backgroundIdeAgentRun,
    closeTerminalSession,
    createTerminalSession,
    createVaxonTerminalSession,
    loadTerminalSessions,
    renameTerminalSession,
    setActiveTerminalSession,
    splitTerminalSession,
  } = terminalSessionStore;

  const activeWorkspaceFilePath = computed(() => {
    const path = filePathFromDocumentId(activeEditorDocumentId.value);
    return path && openedFilePaths.value.includes(path) ? path : null;
  });
  const hasEditorSelection = computed(() => Boolean(editorSelection.value?.text.trim()));

  function setEditorSelection(selection: EditorSelectionSnapshot | null): void {
    editorSelection.value = selection;
  }

  function setActiveEditorTab(id: string): void {
    activeEditorTabId.value = id;
  }

  function migrateMarkdownAgentReviewDraft(id: string): boolean {
    if (!isAgentEditReviewDocumentId(id)) {
      return false;
    }
    const draft = draftDocuments.value.find((document) => document.id === id);
    const reviewPath =
      draft?.filePath ||
      (() => {
        const match = /^#\s*Agent review ·\s+(.+?)\s*$/m.exec(draft?.value || '');
        return match?.[1]?.trim() || null;
      })();
    if (!reviewPath || !isMarkdownAgentEditPath(reviewPath)) {
      return false;
    }
    draftDocuments.value = draftDocuments.value.filter((document) => document.id !== id);
    persistEditorMarkdownPreviewEnabled(workspaceFileDocumentId(reviewPath), true);
    void openWorkspaceFile(reviewPath);
    return true;
  }

  function setActiveEditorDocument(id: string): void {
    // Stale markdown agent-review drafts (green + lines / no Preview) → open the real file.
    if (migrateMarkdownAgentReviewDraft(id)) {
      return;
    }

    activeEditorDocumentId.value = id;
    editorSelection.value = null;
    const path = filePathFromDocumentId(id);
    if (path) {
      void openWorkspaceFile(path);
    }
  }

  // Also migrate if a green markdown review tab is already active (e.g. after reload).
  watch(
    activeEditorDocumentId,
    (id) => {
      migrateMarkdownAgentReviewDraft(id);
    },
    { flush: 'post' },
  );

  function closeEditorDocument(id: string): void {
    const path = filePathFromDocumentId(id);
    const openTabs = editorDocuments.value.filter(
      (document) => document.source === 'file' || document.source === 'draft',
    );
    const closingIndex = openTabs.findIndex((document) => document.id === id);
    if (closingIndex < 0) {
      return;
    }

    if (path) {
      openedFilePaths.value = openedFilePaths.value.filter((entry) => entry !== path);
    } else {
      draftDocuments.value = draftDocuments.value.filter((document) => document.id !== id);
    }

    if (activeEditorDocumentId.value !== id) {
      return;
    }

    const remaining = openTabs.filter((document) => document.id !== id);
    if (remaining.length === 0) {
      activeEditorDocumentId.value = 'file:README.md';
      if (!openedFilePaths.value.includes('README.md')) {
        openedFilePaths.value = ['README.md'];
      }
      void openWorkspaceFile('README.md');
      return;
    }

    const nextIndex = closingIndex >= remaining.length ? remaining.length - 1 : closingIndex;
    setActiveEditorDocument(remaining[nextIndex].id);
  }

  function revealEditorLine(line: number): void {
    if (line < 1) {
      return;
    }
    editorRevealRequest.value = {
      line,
      nonce: Date.now(),
    };
  }

  async function reloadWorkspaceFile(path: string): Promise<void> {
    const workspaceId = currentWorkspace.value?.workspace_id;
    if (!workspaceId) {
      return;
    }

    if (isImageFilePath(path)) {
      fileContentLoadStates.value = {
        ...fileContentLoadStates.value,
        [path]: 'loaded',
      };
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
      fileSavedContents.value = {
        ...fileSavedContents.value,
        [path]: payload.content,
      };
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
        error instanceof Error ? error.message : 'workspace file reload failed';
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

    if (isImageFilePath(path)) {
      fileContentLoadStates.value = {
        ...fileContentLoadStates.value,
        [path]: 'loaded',
      };
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

  async function openWorkspaceFile(
    path: string,
    reveal: { line?: number; searchText?: string } | null = null,
  ): Promise<void> {
    const normalizedPath = normalizeWorkspaceFilePath(path);
    if (!openedFilePaths.value.includes(normalizedPath)) {
      openedFilePaths.value = [...openedFilePaths.value, normalizedPath];
    }

    editorRevealRequest.value = reveal
      ? {
          line: reveal.line,
          searchText: reveal.searchText?.trim() || undefined,
          nonce: Date.now(),
        }
      : null;

    activeEditorDocumentId.value = workspaceFileDocumentId(normalizedPath);
    await ensureWorkspaceFileLoaded(normalizedPath);
  }

  function proveResearchSource(options: {
    title: string;
    url: string;
    snippet: string;
    query?: string;
    kind?: ResearchBlockKind;
  }): void {
    const target = resolveResearchFlyToTarget({
      title: options.title,
      url: options.url,
      snippet: options.snippet,
      query: options.query,
    });
    if (target) {
      void openWorkspaceFile(target.path, {
        line: target.line,
        searchText: target.searchText,
      });
      return;
    }
    const url = options.url.trim();
    if (url && url !== 'about:blank') {
      window.open(url, '_blank', 'noopener,noreferrer');
    }
  }

  function openResearchInEditor(options: {
    title: string;
    url: string;
    snippet: string;
  }): void {
    const title = options.title.trim() || 'Research source';
    const snippet = options.snippet.trim();
    if (!snippet) {
      return;
    }
    openAgentContentInEditor({
      title,
      content: buildResearchEditorContent(title, options.url.trim(), snippet),
      preferPreview: true,
    });
  }

  function openAgentContentInEditor(options: {
    title: string;
    content: string;
    preferPreview?: boolean;
    focus?: boolean;
  }): string | null {
    const title = formatAgentDraftTitle(options.title.trim() || 'Agent response');
    const content = options.content.trim();
    if (!content) {
      return null;
    }
    const shouldFocus = options.focus !== false;

    const normalizedTitle = title.toLowerCase();
    const existing = draftDocuments.value.find(
      (document) => document.source === 'draft' && document.title.toLowerCase() === normalizedTitle,
    );

    if (existing) {
      draftDocuments.value = draftDocuments.value.map((document) =>
        document.id === existing.id
          ? { ...document, value: content, dirty: document.value !== content }
          : document,
      );
      if (shouldFocus) {
        activeEditorDocumentId.value = existing.id;
      }
      return existing.id;
    }

    const slug = normalizedTitle.replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 48);
    const id = `draft:agent-${slug || 'response'}-${Date.now().toString(36)}`;
    draftDocuments.value = [
      ...draftDocuments.value,
      {
        id,
        title,
        language: 'markdown',
        value: content,
        description: 'Agent response opened in the editor. Raw/Preview toggle is in the tab bar.',
        source: 'draft',
        readOnly: false,
        dirty: false,
      },
    ];
    if (shouldFocus) {
      activeEditorDocumentId.value = id;
    }

    if (options.preferPreview !== false) {
      persistEditorMarkdownPreviewEnabled(id, true);
    }

    return id;
  }

  function openAgentEditReview(edit: Pick<IdeAgentEditSummary, 'path' | 'diff' | 'added' | 'removed' | 'open'>): void {
    const path = normalizeEditedFilePath(edit.path);
    if (shouldOpenWorkspaceFileForEditReview(edit)) {
      if (layoutMode.value !== 'ide') {
        setLayoutMode('ide');
      }
      // Markdown edits are already on disk — open the real file with Preview enabled.
      if (languageForFilePath(path) === 'markdown') {
        persistEditorMarkdownPreviewEnabled(workspaceFileDocumentId(path), true);
      }
      void openWorkspaceFile(path);
      return;
    }

    if (layoutMode.value !== 'ide') {
      setLayoutMode('ide');
    }

    if (!openedFilePaths.value.includes(path)) {
      openedFilePaths.value = [...openedFilePaths.value, path];
      void ensureWorkspaceFileLoaded(path);
    }

    const id = agentEditReviewDocumentId(path);
    const title = agentEditReviewDocumentTitle(path);
    const content = formatAgentEditReviewContent(edit);
    const language = (
      languageForFilePath(path) === 'markdown' ? 'markdown' : 'plaintext'
    ) as EditorDocumentLanguage;
    const existing = draftDocuments.value.find((document) => document.id === id);

    if (existing) {
      draftDocuments.value = draftDocuments.value.map((document) =>
        document.id === id
          ? {
              ...document,
              title,
              language,
              value: content,
              dirty: document.value !== content,
            }
          : document,
      );
    } else {
      draftDocuments.value = [
        ...draftDocuments.value,
        {
          id,
          title,
          language,
          value: content,
          description:
            language === 'markdown'
              ? 'Agent markdown review (Preview/Raw). Diff markers are stripped for readable rendering.'
              : 'Agent proposed changes from the transcript diff (read-only review).',
          source: 'draft',
          readOnly: true,
          dirty: false,
          filePath: path,
        },
      ];
    }

    if (language === 'markdown') {
      persistEditorMarkdownPreviewEnabled(id, true);
    }
    activeEditorDocumentId.value = id;
  }

  function recordAgentReportEditorLink(
    messageId: string,
    link: AgentReportEditorLink,
  ): void {
    agentReportEditorLinksByMessageId.value = {
      ...agentReportEditorLinksByMessageId.value,
      [messageId]: link,
    };
  }

  function agentReportEditorLink(messageId: string): AgentReportEditorLink | null {
    return agentReportEditorLinksByMessageId.value[messageId] ?? null;
  }

  function focusAgentReportEditor(messageId: string): void {
    const link = agentReportEditorLink(messageId);
    if (link) {
      activeEditorDocumentId.value = link.documentId;
    }
  }

  function setCurrentWorkspace(workspaceId: string): void {
    const previousWorkspaceId = currentWorkspace.value?.workspace_id ?? null;
    if (previousWorkspaceId && previousWorkspaceId !== workspaceId) {
      // Persist outgoing workspace tabs before we wipe/replace the open set.
      persistOpenEditorTabs(previousWorkspaceId);
      stashWorkspaceIdeView(previousWorkspaceId);
      openedFilePaths.value = [];
      activeEditorDocumentId.value = 'file:README.md';
    }
    operatorPinnedWorkspaceId.value = workspaceId;
    persistOperatorWorkspaceId(workspaceId);
    syncCurrentWorkspace(workspaceId);
    if (previousWorkspaceId !== workspaceId) {
      syncIdeComposerDraftForWorkspace(workspaceId);
      void refreshOperatorThreadMessages(workspaceId);
      void restoreWorkspaceIdeView(workspaceId);
      void loadRunHistory(selectWorkspacePrimaryRun(
        runs.value.filter((run) => run.workspace_id === workspaceId),
      )?.run_id ?? null);
      void loadOperatorBriefing({ background: briefingLoadState.value === 'loaded' });
      void loadTerminalSessions(workspaceId);
    }
    void loadWorkspaceFiles();
  }

  let suppressOpenTabsPersist = false;

  function persistOpenEditorTabs(workspaceId: string | null | undefined = currentWorkspace.value?.workspace_id): void {
    if (suppressOpenTabsPersist) {
      return;
    }
    const id = String(workspaceId || '').trim();
    if (!id) {
      return;
    }
    // Never persist an empty set over a known saved session (e.g. mid-switch wipe).
    if (openedFilePaths.value.length === 0) {
      const existing = readOpenEditorFilePathsByWorkspace()[id] ?? [];
      if (existing.length > 0) {
        return;
      }
    }
    writeOpenEditorFilePathsForWorkspace(id, openedFilePaths.value);
    const activeId = activeEditorDocumentId.value.trim();
    if (activeId.startsWith('file:')) {
      writeActiveEditorDocumentIdForWorkspace(id, activeId);
    }
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
      // Workspace may have changed while the request was in flight.
      if (currentWorkspace.value?.workspace_id !== workspaceId) {
        return;
      }

      workspaceFileEntries.value = snapshot.items;
      fileContents.value = {};
      fileSavedContents.value = {};
      fileContentLoadStates.value = {};
      workspaceFilesLoadState.value = 'loaded';

      const availablePaths = snapshot.items.map((entry) => entry.path);
      const preferredPath = pickPreferredWorkspaceFilePath(snapshot.items);
      // Keep in-session tabs across file-tree reloads; on hard refresh use localStorage.
      const storedPaths = readOpenEditorFilePathsByWorkspace()[workspaceId] ?? [];
      const candidatePaths =
        openedFilePaths.value.length > 0 ? openedFilePaths.value : storedPaths;

      suppressOpenTabsPersist = true;
      let restoredPaths: string[] = [];
      try {
        restoredPaths = restoreOpenEditorFilePaths(
          candidatePaths,
          availablePaths,
          preferredPath,
        );
        openedFilePaths.value = restoredPaths;

        const storedActiveId = readActiveEditorDocumentIdsByWorkspace()[workspaceId] ?? null;
        const currentPath = filePathFromDocumentId(activeEditorDocumentId.value);
        const restoredActiveId = resolveRestoredActiveEditorDocumentId({
          storedDocumentId:
            activeEditorDocumentId.value.startsWith('file:') &&
            currentPath &&
            restoredPaths.includes(currentPath)
              ? activeEditorDocumentId.value
              : storedActiveId,
          openedPaths: restoredPaths,
        });
        if (restoredActiveId) {
          activeEditorDocumentId.value = restoredActiveId;
        }
      } finally {
        suppressOpenTabsPersist = false;
      }

      persistOpenEditorTabs(workspaceId);

      await Promise.all(
        restoredPaths.map((path) => ensureWorkspaceFileLoaded(path)),
      );
    } catch (error) {
      if (currentWorkspace.value?.workspace_id !== workspaceId) {
        return;
      }
      workspaceFilesLoadState.value = 'error';
      workspaceFilesError.value =
        error instanceof Error ? error.message : 'workspace files request failed';
    }
  }

  const { createWorkspaceFile, createWorkspaceFolder, renameActiveWorkspaceFile } =
    createWorkspaceFileOps({
      currentWorkspace,
      workspaceFilesError,
      workspaceFileEntries,
      fileSaveState,
      fileSaveError,
      fileContents,
      fileSavedContents,
      fileContentLoadStates,
      activeWorkspaceFilePath,
      activeEditorDocumentId,
      openedFilePaths,
      openWorkspaceFile,
      loadWorkspaceFiles,
      ensureWorkspaceFileLoaded,
    });

  watch(
    [openedFilePaths, activeEditorDocumentId, () => currentWorkspace.value?.workspace_id],
    () => {
      persistOpenEditorTabs();
    },
    { deep: true },
  );

  function updateActiveFileContent(value: string): void {
    const document = activeEditorDocument.value;
    if (document?.source === 'draft') {
      if (document.readOnly && document.value.trim() && !value.trim()) {
        return;
      }
      draftDocuments.value = draftDocuments.value.map((entry) =>
        entry.id === document.id ? { ...entry, value, dirty: entry.value !== value } : entry,
      );
      return;
    }

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

  const {
    loadRuntimeSummary,
  } = createRuntimeSummarySlice({
    runtimeSummary,
    runtimeSummaryLoadState,
    runtimeSummaryError,
  });

  const {
    loadRuntimeMcpTools,
    loadRuntimeStatus,
  } = createRuntimeProbesSlice({
    runtimeStatus,
    runtimeStatusLoadState,
    runtimeStatusError,
    runtimeMcpTools,
    runtimeMcpToolsLoadState,
  });

  const {
    composerRuntimePrefs,
    selectedRuntimeTargetId,
    selectedComposerModel,
    cursorCatalogRows,
    cursorPickerVisibleModelIds,
    composerRuntimeLabel,
    setSelectedRuntimeTarget,
    setSelectedComposerModel,
    toggleCursorPickerVisibleModel,
  } = createComposerRuntimePrefsSlice({
    currentWorkspace,
    runtimeStatus,
    cursorRuntimeStatus,
    composerRuntimePrefsRevision,
    cursorPickerVisibleRevision,
  });

  const {
    loadCursorCatalog,
    migrateCursorComposerModelIfNeeded,
  } = createCursorCatalogSlice({
    cursorRuntimeStatus,
    cursorCatalogLoadState,
    cursorCatalogError,
    cursorCatalogRows,
    composerRuntimePrefsRevision,
    currentWorkspaceId: () => currentWorkspace.value?.workspace_id ?? null,
  });

  const {
    loadConnectors,
    refreshWatchSummary,
    reprobeConnector,
    startCloudflareTunnel,
    stopCloudflareTunnel,
  } = createConnectorsSlice({
    connectorsItems,
    connectorsSummary,
    connectorsLoadState,
    connectorsError,
    connectorMutationPending,
    loadRuntimeSummary: () => loadRuntimeSummary(),
    loadInbox: () => loadInbox(),
    loadOperatorBriefing: () => loadOperatorBriefing(),
    loadOperatorFleetHealth: () => loadOperatorFleetHealth(),
  });

  async function testKairoVoiceFromSettings(): Promise<'azure' | 'browser' | 'skipped'> {
    if (
      operatorPresenceSettings.value.privacy_mode ||
      effectiveKairoNarrationLevel.value === 'off'
    ) {
      return 'skipped';
    }
    setKairoConversationPhase('speaking');
    kairoVoicePaused.value = false;
    try {
      const result = await speakKairoLine('Systems are up — voice delivery looks good from here.');
      return result.engine === 'idle' ? 'skipped' : result.engine;
    } finally {
      if (kairoConversationPhase.value === 'speaking') {
        setKairoConversationPhase('idle');
      }
    }
  }

  const briefingLoader = {
    load: async (_options?: {
      viewportCompact?: boolean;
      background?: boolean;
    }): Promise<void> => {},
  };

  const {
    mobileCompactLayout,
    getLastViewportCompactRequested,
    setLastViewportCompactRequested,
    bindViewportCompactListener,
    unbindViewportCompactListener,
  } = createViewportCompactSlice({
    viewportWidth,
    operatorBriefing,
    operatorPresenceSettings,
    loadOperatorBriefing: (options) => briefingLoader.load(options),
  });

  const {
    loadOperatorBriefing,
  } = createOperatorBriefingSlice({
    operatorBriefing,
    briefingLoadState,
    briefingError,
    approvals,
    viewportWidth,
    operatorPresenceSettings,
    currentWorkspaceId: () => currentWorkspace.value?.workspace_id ?? null,
    applyOperatorDockDefaults,
    getLastViewportCompactRequested,
    setLastViewportCompactRequested,
  });
  briefingLoader.load = loadOperatorBriefing;

  const {
    loadOperatorPresenceSettings,
    saveOperatorPresenceSettingsPatch,
    resetOperatorPresenceSettings,
    openOperatorPresenceSettingsPanel,
    toggleOperatorPresenceSettingsPanel,
  } = createOperatorPresenceSettingsSlice({
    operatorPresenceSettings,
    operatorPresenceSettingsOpen,
    operatorPresenceSettingsSaving,
    operatorPresenceSettingsError,
    operatorPresenceSettingsSavedAt,
    loadOperatorBriefing: () => loadOperatorBriefing(),
  });

  const {
    loadInbox,
    dismissInboxSignalIds,
    verifyAndDismissHandoffSignal,
    dismissLinkedHandoffSignalAfterRunComplete,
    clearActiveSignals,
  } = createInboxSignalsSlice({
    inboxItems,
    signalViews,
    inboxLoadState,
    inboxError,
    signalClearState,
    signalClearError,
    highlightedSignalId,
    pendingHandoffDismissSignalId,
    operatorBriefing,
    loadOperatorBriefing: () => loadOperatorBriefing(),
    loadRuntimeSummary: () => loadRuntimeSummary(),
  });

  const {
    loadOperatorBrainGraph,
    loadOperatorFleetHealth,
  } = createOperatorProbesSlice({
    operatorFleetHealth,
    operatorFleetHealthLoadState,
    operatorFleetHealthError,
    operatorBrainGraph,
    operatorBrainGraphLoadState,
    operatorBrainGraphError,
  });

  async function refreshOperatorPresence(): Promise<void> {
    await loadOperatorBriefing({ background: true });
  }

  async function refreshRunSurfaces(): Promise<void> {
    const briefingBackground = briefingLoadState.value === 'loaded';
    const runtimeBackground = runtimeSummaryLoadState.value === 'loaded';
    const inboxBackground = inboxLoadState.value === 'loaded';
    await Promise.all([
      loadRuns(),
      loadRuntimeStatus(),
      loadRuntimeSummary({ background: runtimeBackground }),
      loadInbox({ background: inboxBackground }),
      loadConnectors(),
      loadOperatorBriefing({ background: briefingBackground }),
      loadOperatorFleetHealth({ background: operatorFleetHealthLoadState.value === 'loaded' }),
      operatorBrainGraphLoadState.value === 'loaded'
        ? loadOperatorBrainGraph({ background: true })
        : Promise.resolve(),
    ]);
    await loadRunHistory(primaryActiveRun.value?.run_id ?? null);
    await flushIdeComposerQueueIfIdle();
  }

  async function completeAllReviewReadyRuns(): Promise<void> {
    const workspaceId = currentWorkspace.value?.workspace_id ?? null;
    const targets = runs.value.filter(
      (run) =>
        run.phase === 'review_ready' &&
        isOperatorCompletablePhase(run.phase) &&
        (!workspaceId || run.workspace_id === workspaceId),
    );
    if (!targets.length || runMutationPending.value) {
      return;
    }

    runMutationState.value = 'completing';
    runMutationError.value = null;

    try {
      for (const run of targets) {
        await completeRun(run.run_id);
      }
      await refreshRunSurfaces();
      await dismissLinkedHandoffSignalAfterRunComplete();
      afterRunLifecycleMutation();
    } catch (error) {
      runMutationError.value =
        error instanceof Error ? error.message : 'complete all review-ready runs failed';
    } finally {
      runMutationState.value = 'idle';
    }
  }

  async function stopIdeAgentRun(): Promise<void> {
    if (runMutationPending.value) {
      return;
    }

    stopKairoSpeech();
    const run = resolveActiveIdeStopRun();
    const workspaceId = currentWorkspace.value?.workspace_id ?? undefined;
    runMutationState.value = 'stopping';
    runMutationError.value = null;
    disconnectChatStreamSession(workspaceId);
    agentStreamActive.value = false;
    agentStreamMessageId.value = null;
    ideComposerActivity.value = null;
    if (workspaceId) {
      setWorkspaceStreamUi(workspaceId, {
        active: false,
        messageId: null,
        activity: null,
      });
    }

    if (!run) {
      runMutationError.value = 'No active run to stop.';
      runMutationState.value = 'idle';
      void flushIdeComposerQueueIfIdle();
      return;
    }

    try {
      await stopRun(run.run_id);
      await refreshRunSurfaces();
      const updated = runs.value.find((record) => record.run_id === run.run_id);
      if (shouldClearIdeAgentRunLink(updated)) {
        clearIdeAgentRunLink();
      }
    } catch (error) {
      runMutationError.value = error instanceof Error ? error.message : 'stop run request failed';
    } finally {
      runMutationState.value = 'idle';
      void flushIdeComposerQueueIfIdle();
    }
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

  async function resumeIdeAgentRun(): Promise<void> {
    const run = ideAgentLinkedRun.value;
    if (!run?.can_resume || runMutationPending.value) {
      return;
    }

    runMutationState.value = 'resuming';
    runMutationError.value = null;

    try {
      const latestPrompt = latestIdeOperatorPromptForRun(run.run_id);
      if (latestPrompt) {
        const dispatched = await dispatchIdeComposerMessage('agent', {
          contentOverride: latestPrompt,
          linkedRunIdOverride: run.run_id,
          clearDraftOnSuccess: false,
        });
        if (dispatched) {
          await refreshRunSurfaces();
          const updated = ideAgentLinkedRun.value;
          if (updated && updated.phase !== 'paused' && updated.phase !== 'review_ready') {
            afterRunLifecycleMutation();
            return;
          }
        }
      }

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
      await dismissLinkedHandoffSignalAfterRunComplete();
      afterRunLifecycleMutation();
    } catch (error) {
      runMutationError.value =
        error instanceof Error ? error.message : 'complete run request failed';
    } finally {
      runMutationState.value = 'idle';
    }
  }

  async function approveIdeAgentRun(): Promise<void> {
    const run = ideAgentLinkedRun.value;
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

  async function rejectIdeAgentRun(): Promise<void> {
    const run = ideAgentLinkedRun.value;
    if (run?.phase !== 'awaiting_approval' || runMutationPending.value) {
      return;
    }

    runMutationState.value = 'rejecting';
    runMutationError.value = null;

    try {
      await rejectRun(run.run_id);
      clearIdeAgentRunLink();
      await refreshRunSurfaces();
    } catch (error) {
      runMutationError.value = error instanceof Error ? error.message : 'reject run request failed';
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
    await loadOperatorPresenceSettings();
    // Select a workspace before the heavier runtime/fleet probes so the IDE
    // explorer + terminal are not stuck on "No workspace selected" while a
    // single-worker control-plane is busy with CLI auth probes.
    await loadWorkspaces({ sync: false });
    await loadRuns({ sync: false });
    syncCurrentWorkspace(
      operatorPinnedWorkspaceId.value ??
        defaultOperatorWorkspaceId(workspaces.value),
    );
    const workspaceId = currentWorkspace.value?.workspace_id;
    if (workspaceId) {
      await loadTerminalSessions(workspaceId);
      void loadWorkspaceFiles();
      syncIdeComposerDraftForWorkspace(workspaceId);
    }

    await Promise.all([
      loadRuntimeStatus(),
      loadRuntimeSummary(),
      loadInbox(),
      loadConnectors(),
      loadOperatorBriefing(),
      loadOperatorFleetHealth(),
    ]);
    await loadRunHistory(primaryActiveRun.value?.run_id ?? null);
    if (workspaceId) {
      await loadWorkspaceThread(workspaceId, 'operator');
      await hydrateWorkspaceIdeChat(workspaceId);
      if (layoutMode.value === 'operator') {
        threadMessages.value = operatorThreadMessages.value;
      }
    }
    applyOperatorDockDefaults();
  }

  return {
    activeEditorTabId,
    activeEditorDocument,
    activeEditorDocumentId,
    editorSelection,
    hasEditorSelection,
    setEditorSelection,
    activeRun,
    agentExecutionAccess,
    activeTerminalSessionId,
    activeWorkspaceFilePath,
    approveIdeAgentRun,
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
    canApproveIdeAgentRun,
    canApprovePrimaryRun,
    canCompletePrimaryRun,
    canMarkPrimaryRunReviewReady,
    canRejectPrimaryRun,
    canResumeIdeAgentRun,
    currentWorkspace,
    editorDocuments,
    canResumePrimaryRun,
    canStopPrimaryRun,
    canStopIdeAgentRun,
    canSubmitOperatorCommand,
    canSubmitIdeComposer,
    composerAgentBusy,
    ideComposerQueue,
    ideComposerQueueSummary,
    commandMutationError,
    commandMutationState,
    commandFocusToken,
    composerRuntimeLabel,
    composerRuntimePrefs,
    commandSeamHint,
    cursorCatalogError,
    cursorCatalogLoadState,
    cursorCatalogRows,
    cursorPickerVisibleModelIds,
    cursorRuntimeStatus,
    dockContext,
    dockHeroMode,
    dockSeamLayout,
    dockSeamState,
    editorTabs,
    inboxError,
    ideAgentLinkedRun,
    ideAgentRunId,
    ideComposerActivity,
    activeIdeThreadId,
    ideThreadsForCurrentWorkspace,
    openIdeThreadTabsForCurrentWorkspace,
    activeTerminalSession,
    ideDisplayKairoPresenceState,
    idePresenceProfile,
    inboxItems,
    inboxLoadState,
    activeOperatorSignalCount,
    attentionSignals,
    workspaceAttentionSignalCount,
    inboxStateLabel,
    kairoBriefingAttention,
    kairoAgentLiveLine,
    kairoBriefingAttentionLabel,
    kairoPresenceState,
    effectiveKairoNarrationLevel,
    agentStreamActive,
    agentStreamMessageId,
    agentReportEditorLink,
    focusAgentReportEditor,
    agentDockCollapsed,
    ideActivityView,
    ideExplorerCollapsed,
    ideAttentionPanelOpen,
    closeIdeAttentionPanel,
    ideBriefingPanelOpen,
    closeIdeBriefingPanel,
    openIdeBriefingPanel,
    ideTerminalRevealToken,
    ideTerminalToggleToken,
    layoutMode,
    layoutModeLabel,
    leftSidebarAttentionBadgeCount,
    leftSidebarMode,
    mobileCompactLayout,
    viewportWidth,
    clearActiveSignals,
    verifyAndDismissHandoffSignal,
    completePrimaryRun,
    completeAllReviewReadyRuns,
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
    loadOperatorBrainGraph,
    loadOperatorBriefing,
    loadOperatorFleetHealth,
    loadOperatorPresenceSettings,
    loadRuns,
    loadCursorCatalog,
    loadRuntimeStatus,
    loadRuntimeSummary,
    loadWorkspaceThread,
    loadIdeThreads,
    hydrateWorkspaceIdeChat,
    createIdeThread,
    selectIdeThread,
    closeIdeThreadTab,
    loadTerminalSessions,
    setActiveTerminalSession,
    createTerminalSession,
    createVaxonTerminalSession,
    backgroundIdeAgentRun,
    splitTerminalSession,
    renameTerminalSession,
    closeTerminalSession,
    loadWorkspaces,
    markPrimaryRunReviewReady,
    operatorBrainGraph,
    operatorBrainGraphError,
    operatorBrainGraphLoadState,
    operatorBrainGalaxyActive,
    operatorCenterView,
    operatorBriefing,
    briefingVoiceTranscript,
    operatorFleetHealth,
    operatorFleetHealthError,
    operatorFleetHealthLoadState,
    operatorCommandDraft,
    ideComposerDraft,
    operatorPresenceSettings,
    operatorPresenceSettingsOpen,
    operatorPresenceSettingsSaving,
    operatorPresenceSettingsError,
    operatorPresenceSettingsSavedAt,
    createWorkspaceFile,
    createWorkspaceFolder,
    pendingApprovalsCount,
    primaryActiveRun,
    primaryApprovalRun,
    primaryInboxItem,
    refreshRunSurfaces,
    refreshOperatorPresence,
    refreshWatchSummary,
    rejectIdeAgentRun,
    rejectPrimaryRun,
    reprobeConnector,
    startCloudflareTunnel,
    stopCloudflareTunnel,
    runOperatorCommand,
    resumePrimaryRun,
    resumeIdeAgentRun,
    revealIdeTerminalPanel,
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
    runtimeStatus,
    runtimeStatusError,
    runtimeStatusLoadState,
    runtimeMcpTools,
    runtimeMcpToolsLoadState,
    loadRuntimeMcpTools,
    runtimeSummary,
    runtimeSummaryError,
    runtimeSummaryLoadState,
    showDevSeams,
    showKairoBriefingAttention,
    statusBarItems,
    statusBarSegments,
    statusBarZones,
    renameActiveWorkspaceFile,
    closeEditorDocument,
    revealEditorLine,
    setActiveEditorTab,
    setActiveEditorDocument,
    setCurrentWorkspace,
    setDockHeroMode,
    setIdeActivityView,
    selectedComposerModel,
    selectedRuntimeTargetId,
    setSelectedComposerModel,
    setSelectedRuntimeTarget,
    setAgentExecutionAccess,
    setOperatorCenterView,
    setLayoutMode,
    setLeftSidebarMode,
    toggleCursorPickerVisibleModel,
    toggleAgentDock,
    toggleIdeExplorer,
    signalClearError,
    signalClearState,
    signalViews,
    stopPrimaryRun,
    stopIdeAgentRun,
    submitOperatorCommand,
    submitOperatorCommandContent,
    handoffSignalToIde,
    handoffDiscussedSignalToIde,
    handoffMutationState,
    handoffMutationError,
    pendingHandoffDismissSignalId,
    lastDiscussedSignal,
    submitIdeComposer,
    steerIdeComposer,
    steerQueuedIdeComposerMessage,
    removeIdeComposerQueuedMessage,
    terminalSessions,
    threadMessages,
    operatorThreadMessages,
    latestWorkspaceAgentOutput,
    threadStateLabel,
    toggleDockSeam,
    toggleDockHeroMode,
    toggleOperatorPresenceSettingsPanel,
    openOperatorPresenceSettingsPanel,
    toggleSignalDetails,
    topbarBreadcrumb,
    topbarChips,
    topbarMetaPills,
    fileSaveError,
    fileSaveState,
    editorRevealRequest,
    focusCommandSeam,
    restoreComposerDraft,
    focusAttentionSidebar,
    focusMissionControl,
    focusKairoBriefing,
    deliverKairoSpokenAlert,
    speakOperatorBriefing,
    speakKairoConversationLine,
    stopKairoSpeech,
    pauseKairoSpeech,
    resumeKairoSpeech,
    interruptKairoVoice,
    handleKairoPresenceAction,
    kairoSpeechActive,
    kairoSpeechSessionId,
    kairoVoicePaused,
    maybeSpeakBootGreeting,
    loadWorkspaceFiles,
    openAgentContentInEditor,
    openAgentEditReview,
    openWorkspaceFile,
    openResearchInEditor,
    proveResearchSource,
    saveActiveFileDocument,
    saveOperatorPresenceSettingsPatch,
    resetOperatorPresenceSettings,
    testKairoVoiceFromSettings,
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
