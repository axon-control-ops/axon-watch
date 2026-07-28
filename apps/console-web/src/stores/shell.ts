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
  RuntimeStatusSnapshot,
  TerminalSessionRecord,
  WorkspaceChatThreadListItem,
} from '../api/control-plane';
import {
  readStoredOperatorCenterView,
  type BrainGraphSnapshot,
  type OperatorCenterView,
} from '../lib/operator-brain-graph-view';
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
import { editedFilePathsFromTranscript } from '../lib/agent-transcript-blocks';
import { buildResearchEditorContent } from '../lib/prove-research-source';
import { resolveResearchFlyToTarget } from '../lib/research-fly-to-source';
import type { ResearchBlockKind } from '../lib/research-provider';
import {
  createAgentStreamIncrementalState,
  createAgentStreamVoiceSession,
  handleAgentStreamVoiceDelta,
} from '../lib/agent-stream-voice-session';
import { createRafStreamUiBatcher } from '../lib/stream-ui-raf-batch';
import { createStreamMessageContentBatcher } from '../lib/stream-message-content-batch';
import {
  resolveBootstrapIdeThreadId,
  shouldApplyWorkspaceThreadLoad,
} from '../lib/workspace-thread-load';
import {
  createWorkspaceThreadLoadQueue,
  loadWorkspaceThreadOnce,
} from '../lib/load-workspace-thread';
import { effectiveKairoNarration } from '../lib/kairo-narration-policy';
import { postKairoSpeak } from '../lib/kairo-speak-client';
import type { EditorRevealRequest } from '../components/EditorHost.vue';
import type { EditorSelectionSnapshot } from '../lib/create-monaco-editor';
import { DEFAULT_OPERATOR_TERMINAL_SESSION_ID } from '../lib/terminal-session-view';
import {
  createTerminalSessionStore,
  DEFAULT_TERMINAL_SESSIONS,
  type TerminalSessionDescriptor,
} from '../lib/shell-terminal-session-store';
import { createWorkspaceFileOps } from '../lib/shell-workspace-file-ops';
import { sortIdeThreadsNewestFirst } from '../lib/ide-thread-picker-view';
import { employeeIdeThreadTitle } from '../features/workspace-agents/employee-thread';
import {
  ensureOpenIdeThreadTabs,
  openIdeThreadTab,
  pruneOpenIdeThreadTabs,
  resolveIdeThreadTabAfterClose,
  resolveOpenIdeThreadTabItems,
  seedOpenIdeTabsFromHistory,
} from '../lib/ide-thread-tabs-view';
import {
  readOpenIdeThreadIdsByWorkspace,
  writeOpenIdeThreadIdsForWorkspace,
} from '../lib/ide-thread-tabs-prefs';
import { ideVoiceSpeechAllowed } from '../lib/ide-voice-strip';
import {
  clearIdeRunRecovery,
  fetchControlPlaneBootId,
  persistIdeRunRecovery,
  readIdeRunRecovery,
} from '../lib/ide-run-recovery';
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
import { employeeVoiceSpeaker } from '../lib/kairo-voice-utterance';
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
import { isRunLinkedComposerMode, isToolCapableComposerMode } from '../lib/composer-tool-modes';
import {
  persistIdeComposerDraft,
  readStoredIdeComposerDraft,
} from '../lib/ide-composer-draft-prefs';
import {
  defaultWorkspaceStreamUi,
  shouldSyncWorkspaceStreamGlobals,
  streamingThreadIdsFromUiMap,
  workspaceStreamGlobalsFromState,
} from '../lib/workspace-stream-ui';
import { listStaleIdeStreamThreadIds } from '../lib/stale-ide-stream-ui';
import {
  localRuntimeDegradedActive,
  remoteIngressAttentionActive,
} from '../lib/runtime-degraded-scope';
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
import { isOperatorCompletablePhase, resolveAgentContinuePrompt } from '../lib/run-lifecycle-ui';
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
  isBinaryFilePath,
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
import { upsertAgentDraftDocument } from '../lib/agent-draft-document';
import {
  readActiveEditorDocumentIdsByWorkspace,
  readOpenEditorFilePathsByWorkspace,
  resolveRestoredActiveEditorDocumentId,
  restoreOpenEditorFilePaths,
  writeActiveEditorDocumentIdForWorkspace,
  writeOpenEditorFilePathsForWorkspace,
} from '../lib/editor-open-tabs-prefs';
import { formatAgentDraftTitle } from '../lib/editor-tab-labels';
import {
  isAgentEditReviewDocumentId,
  isMarkdownAgentEditPath,
} from '../lib/ide-agent-edit-review';
import { createShellAgentCanvasOps } from '../lib/shell-agent-canvas-ops';
import {
  resolveRunHistoryRunId,
  selectRunSeamDisplayRun,
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
  persistOperatorWorkspaceId,
  readStoredOperatorWorkspaceId,
} from '../lib/operator-workspace-selection';
import {
  defaultOperatorWorkspaceId,
} from '../lib/operator-workspace-catalog';
import {
  DEFAULT_IDE_ACTIVITY_VIEW,
  persistAgentDockCollapsed,
  persistLayoutMode,
  readStoredAgentDockCollapsed,
  readStoredIdeExplorerCollapsed,
  readStoredLayoutMode,
} from '../lib/ide-layout-prefs';
import {
  openIdeComposerSurface,
  openIdeComposerSurfaceWithDraft,
} from './shell/open-ide-composer';
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
import { createIdeRunAutoRecoverySlice } from './shell/slices/create-ide-run-auto-recovery-slice';
import { createInboxSignalsSlice } from './shell/slices/create-inbox-signals-slice';
import { createRuntimeProbesSlice } from './shell/slices/create-runtime-probes-slice';
import { createRuntimeSummarySlice } from './shell/slices/create-runtime-summary-slice';
import { createShellDisplaySlice } from './shell/slices/create-shell-display-slice';
import { createThreadSurfaceSlice } from './shell/slices/create-thread-surface-slice';
import { createCompanyRosterSlice } from './shell/slices/create-company-roster-slice';
import { createBusyEmployeeIdeStreamSlice } from './shell/slices/create-busy-employee-ide-stream-slice';
import { createWorkspaceTasksSlice } from './shell/slices/create-workspace-tasks-slice';
import { createLeadPlansSlice } from './shell/slices/create-lead-plans-slice';
import { createViewportCompactSlice } from './shell/slices/create-viewport-compact-slice';
import { createKairoVoiceSlice } from './shell/slices/create-kairo-voice-slice';
import { createChatStreamSessionSlice } from './shell/slices/create-chat-stream-session-slice';
import { createWorkspaceStreamUiSlice } from './shell/slices/create-workspace-stream-ui-slice';
import { createSignalHandoffSlice } from './shell/slices/create-signal-handoff-slice';
import { createVoiceOrbPlacementController } from './shell/slices/create-voice-orb-placement-slice';
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
  const autoRunRecoveryInFlight = { value: false };
  const agentExecutionAccess = ref<AgentExecutionAccess>(resolveAgentExecutionAccess());
  const ideAgentRunId = ref<string | null>(null);
  const ideComposerActivity = ref<IdeComposerActivity | null>(null);
  const ideDebugModeSelected = ref(false);
  /** Focus thread for stream-global sync — kept in lockstep with activeIdeThreadId. */
  const ideStreamFocusThreadId = ref<string | null>(null);

  const {
    disconnectChatStreamSession,
    disconnectAllChatStreamSessions,
    patchThreadMessageContent,
  } = createChatStreamSessionSlice({
    activeIdeThreadId: ideStreamFocusThreadId,
    threadMessages,
    workspaceIdeThreadMessagesById,
    chatStreamSessionsByWorkspace,
  });

  const {
    getWorkspaceStreamUi,
    applyWorkspaceStreamUiToGlobals,
    setWorkspaceStreamUi,
  } = createWorkspaceStreamUiSlice({
    activeIdeThreadId: ideStreamFocusThreadId,
    workspaceStreamUiById,
    agentStreamActive,
    agentStreamMessageId,
    ideComposerActivity,
    ideAgentRunId,
  });

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
  const activeWorkspaceFilePath = computed(() => {
    const path = filePathFromDocumentId(activeEditorDocumentId.value);
    return path && openedFilePaths.value.includes(path) ? path : null;
  });
  const editorSelection = ref<EditorSelectionSnapshot | null>(null);
  const terminalSessions = ref<TerminalSessionDescriptor[]>(DEFAULT_TERMINAL_SESSIONS);
  const activeTerminalSessionId = ref<string>(DEFAULT_OPERATOR_TERMINAL_SESSION_ID);
  const ideThreadsByWorkspaceId = ref<Record<string, WorkspaceChatThreadListItem[]>>({});
  const openIdeThreadIdsByWorkspaceId = ref<Record<string, string[]>>(
    readOpenIdeThreadIdsByWorkspace(),
  );
  const dockContext = ref<DockContextDescriptor>(DEFAULT_DOCK_CONTEXT);
  const expandedDockSeams = ref<Set<DockSeamId>>(new Set());
  const dockThreadSeamTouched = ref(false);
  const briefingSeamEmphasized = ref(false);
  const missionControlEmphasized = ref(false);
  const connectorsEmphasized = ref(false);
  const signalsSeamEmphasized = ref(false);
  const highlightedSignalId = ref<string | null>(null);
  const dockHeroMode = ref<DockHeroMode>(readStoredDockHeroMode() ?? 'command');
  // Session-only: allow smart defaults (Open loops → briefing) each boot.
  const dockHeroModeTouched = ref(false);
  const commandFocusToken = ref(0);
  const leftSidebarMode = ref<LeftSidebarMode>(readStoredLeftSidebarMode() ?? 'workspaces');
  const leftSidebarModeTouched = ref(Boolean(readStoredLeftSidebarMode()));
  const ideActivityView = ref(DEFAULT_IDE_ACTIVITY_VIEW);
  const ideExplorerCollapsed = ref(readStoredIdeExplorerCollapsed());
  const ideAttentionPanelOpen = ref(false);
  const ideBriefingPanelOpen = ref(false);
  const agentDockCollapsed = ref(readStoredAgentDockCollapsed());
  const ideTerminalRevealToken = ref(0);
  const ideTerminalToggleToken = ref(0);
  const workbenchTerminalPanelVisible = ref(false);
  const teamRosterRevealToken = ref(0);
  const workspaceRuns = computed(() =>
    currentWorkspace.value
      ? runs.value.filter((run) => run.workspace_id === currentWorkspace.value?.workspace_id)
      : runs.value,
  );
  const primaryActiveRun = computed(() => selectWorkspacePrimaryRun(workspaceRuns.value));
  const runSeamDisplayRun = computed(() => selectRunSeamDisplayRun(workspaceRuns.value));

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
    statusBarSegments,
    statusBarItems,
    layoutModeLabel,
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
    connectorsItems,
    connectorsSummary,
    connectorsLoadState,
  });

  const runHistoryRows = computed(() => buildRunHistoryRows(runHistorySnapshot.value));

  const currentWorkspaceIdeThreadMessages = computed(() => {
    if (layoutMode.value === 'ide') {
      return threadMessages.value;
    }
    const threadId = ideStreamFocusThreadId.value ?? activeThreadId.value;
    return (threadId ? workspaceIdeThreadMessagesById.value[threadId] : undefined) ?? [];
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
    if (agentStreamActive.value && isToolCapableComposerMode(ideComposerActivity.value?.mode)) {
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
      runtimeLoaded: Boolean(summary),
    });
  });

  const kairoAgentLiveLine = computed(() => {
    if (!agentStreamActive.value) {
      return null;
    }
    return ideComposerActivity.value?.label ?? null;
  });

  const kairoBriefingAttention = computed(() => {
    const degraded =
      operatorBriefing.value?.degraded ?? runtimeSummary.value?.degraded ?? null;
    return resolveKairoBriefingAttention({
      pendingApprovals: pendingApprovalsCount.value,
      criticalSignals: runtimeSummary.value?.signals.critical_count ?? 0,
      highSignals: runtimeSummary.value?.signals.high_count ?? 0,
      degraded: Boolean(degraded?.active),
      remoteIngressOnly: remoteIngressAttentionActive(degraded),
      briefingLoaded: briefingLoadState.value === 'loaded',
    });
  });

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
      degradedActive: localRuntimeDegradedActive(summary?.degraded),
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
    primaryActiveRun,
    currentWorkspaceId: computed(() => currentWorkspace.value?.workspace_id ?? null),
    operatorThreadMessageCount: computed(() => operatorThreadMessages.value.length),
    leftSidebarMode,
    leftSidebarModeTouched,
    dockHeroMode,
    dockHeroModeTouched,
    briefingSeamEmphasized,
  });

  function stashWorkspaceIdeView(workspaceId: string): void {
    const threadId = activeThreadId.value ?? getWorkspaceSurfaceThreadId(workspaceId, 'ide');
    if (threadId) {
      workspaceIdeThreadMessagesById.value = {
        ...workspaceIdeThreadMessagesById.value,
        [threadId]: [...threadMessages.value],
      };
      setWorkspaceStreamUi(threadId, {
        active: agentStreamActive.value,
        messageId: agentStreamMessageId.value,
        activity: ideComposerActivity.value,
        ideAgentRunId: ideAgentRunId.value,
      });
      setWorkspaceSurfaceThreadId(workspaceId, currentThreadSurface(), threadId);
    }
  }

  async function restoreWorkspaceIdeView(workspaceId: string): Promise<void> {
    await loadIdeThreads(workspaceId);
    const threadId =
      getWorkspaceSurfaceThreadId(workspaceId, 'ide') ?? bootstrapIdeActiveThreadId(workspaceId);
    ideStreamFocusThreadId.value = threadId;
    if (threadId) {
      applyWorkspaceStreamUiToGlobals(threadId);
      const cached = workspaceIdeThreadMessagesById.value[threadId];
      if (cached?.length && isViewingWorkspaceSurface(workspaceId, 'ide')) {
        threadMessages.value = cached;
        activeThreadId.value = threadId;
        commandMutationState.value = 'idle';
        commandMutationError.value = null;
        if (currentWorkspace.value?.workspace_id === workspaceId) {
          syncIdeComposerDraftForWorkspace(workspaceId);
        }
        return;
      }
    }

    await loadWorkspaceThread(workspaceId, 'ide', threadId);
    applyIdeThreadMessagesToView(workspaceId);
    if (currentWorkspace.value?.workspace_id === workspaceId) {
      syncIdeComposerDraftForWorkspace(workspaceId);
    }
  }

  function resetThreadContext(): void {
    const workspaceId = currentWorkspace.value?.workspace_id;
    if (workspaceId) {
      const threadIds = (ideThreadsByWorkspaceId.value[workspaceId] ?? []).map(
        (thread) => thread.thread_id,
      );
      const openIds = openIdeThreadIdsByWorkspaceId.value[workspaceId] ?? [];
      const toClear = new Set([...threadIds, ...openIds, activeThreadId.value].filter(Boolean));
      for (const threadId of toClear) {
        if (!threadId) {
          continue;
        }
        disconnectChatStreamSession(threadId);
        setWorkspaceStreamUi(threadId, {
          active: false,
          messageId: null,
          activity: null,
          ideAgentRunId: null,
        });
        const nextThreadCache = { ...workspaceIdeThreadMessagesById.value };
        delete nextThreadCache[threadId];
        workspaceIdeThreadMessagesById.value = nextThreadCache;
      }
    } else {
      disconnectAllChatStreamSessions();
    }
    agentStreamActive.value = false;
    agentStreamMessageId.value = null;
    agentReportEditorLinksByMessageId.value = {};
    threadMessages.value = [];
    activeThreadId.value = null;
    ideStreamFocusThreadId.value = null;
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

  watch(
    activeIdeThreadId,
    (threadId) => {
      ideStreamFocusThreadId.value = threadId;
      if (threadId) {
        applyWorkspaceStreamUiToGlobals(threadId);
      }
    },
    { immediate: true },
  );

  const ideThreadsForCurrentWorkspace = computed(() => {
    const workspaceId = currentWorkspace.value?.workspace_id;
    if (!workspaceId) {
      return [];
    }
    return sortIdeThreadsNewestFirst(ideThreadsByWorkspaceId.value[workspaceId] ?? []);
  });

  const {
    activeIdeThread,
    activeIdeEmployee,
    activeIdeEmployeeRecord,
    activeIdeEmployeeFailureLine,
    activeIdeEmployeeShiftInterrupted,
    companyEmployeesByWorkspaceId,
    companyEmployeesForCurrentWorkspace,
    loadCompanyEmployees,
  } = createCompanyRosterSlice({
    currentWorkspace,
    activeIdeThreadId,
    ideThreadsForCurrentWorkspace,
    agentStreamActive,
  });

  const {
    workspaceTasksById,
    workspaceTasksForCurrentWorkspace,
    workspaceTasksError,
    workspaceTasksMutating,
    loadWorkspaceTasks,
    createCurrentWorkspaceTask,
    cancelCurrentWorkspaceTask,
  } = createWorkspaceTasksSlice({
    currentWorkspace,
  });

  const {
    leadPlansByWorkspaceId,
    leadPlansForCurrentWorkspace,
    leadPlanIdByTaskId,
    leadPlansError,
    leadPlansMutating,
    loadLeadPlans,
    fanOutCurrentWorkspaceLeadPlan,
    synthesizeCurrentLeadPlan,
  } = createLeadPlansSlice({
    currentWorkspace,
  });

  const workspaceTasksWithPlanLinks = computed(() =>
    workspaceTasksForCurrentWorkspace.value.map((task) => {
      const link = leadPlanIdByTaskId.value.get(task.task_id);
      if (!link) {
        return task;
      }
      return {
        ...task,
        plan_id: link.planId,
        plan_key: link.planKey,
      };
    }),
  );

  /** Fleet-wide roster for cross-workspace speaker avatar resolution. */
  const companyEmployeesFleet = computed(() => {
    const byId = new Map<string, (typeof companyEmployeesForCurrentWorkspace.value)[number]>();
    for (const rows of Object.values(companyEmployeesByWorkspaceId.value)) {
      for (const row of rows) {
        byId.set(row.employee_id, row);
      }
    }
    return [...byId.values()];
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

  const streamingIdeThreadIds = computed(() =>
    streamingThreadIdsFromUiMap(workspaceStreamUiById.value),
  );

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
    const seeded = seedOpenIdeTabsFromHistory({
      openIds: pruned,
      threads,
      activeThreadId: activeId,
    });
    const next = ensureOpenIdeThreadTabs(
      activeId ? openIdeThreadTab(seeded, activeId) : seeded,
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

    disconnectChatStreamSession(threadId);
    setWorkspaceStreamUi(threadId, {
      active: false,
      messageId: null,
      activity: null,
      ideAgentRunId: null,
    });
    const nextCache = { ...workspaceIdeThreadMessagesById.value };
    delete nextCache[threadId];
    workspaceIdeThreadMessagesById.value = nextCache;

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
  const ideChatHydratePromises = new Map<string, Promise<void>>();

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
        [loadedThreadId]: mapped,
      };
      if (currentWorkspace.value?.workspace_id === workspaceId) {
        if (ideStreamFocusThreadId.value === loadedThreadId) {
          ideAgentRunId.value = resolveIdeAgentLinkedRunIdFromMessages(mapped, runs.value);
        }
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
    const cached = threadId ? workspaceIdeThreadMessagesById.value[threadId] : undefined;
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

  async function hydrateWorkspaceIdeChatImpl(workspaceId: string): Promise<void> {
    // Restore cached transcript immediately so the dock does not flash empty while
    // thread list + history requests are in flight.
    applyIdeThreadMessagesToView(workspaceId);
    await loadIdeThreads(workspaceId);
    bootstrapIdeActiveThreadId(workspaceId);
    applyIdeThreadMessagesToView(workspaceId);
    const threadId = getWorkspaceSurfaceThreadId(workspaceId, 'ide');
    if (!threadId) {
      return;
    }
    await loadWorkspaceThread(workspaceId, 'ide', threadId);
    applyIdeThreadMessagesToView(workspaceId);
  }

  async function hydrateWorkspaceIdeChat(workspaceId: string): Promise<void> {
    const cleaned = workspaceId.trim();
    if (!cleaned) {
      return;
    }

    const inflight = ideChatHydratePromises.get(cleaned);
    if (inflight) {
      return inflight;
    }

    const promise = hydrateWorkspaceIdeChatImpl(cleaned).finally(() => {
      ideChatHydratePromises.delete(cleaned);
    });
    ideChatHydratePromises.set(cleaned, promise);
    return promise;
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
      // Flush outgoing thread draft before switching; new tab starts empty.
      flushIdeComposerDraft();
      await selectIdeThread(created.thread_id);
      ideComposerDraft.value = '';
      persistIdeComposerDraft(workspaceId, '', created.thread_id);
      return created.thread_id;
    } catch (error) {
      commandMutationError.value =
        error instanceof Error ? error.message : 'Failed to create a new chat';
      return null;
    }
  }

  /** Find or create a titled IDE thread owned by a company teammate, then focus it. */
  async function openOrFocusEmployeeIdeThread(employee: {
    employee_id: string;
    name: string;
    role: string;
    role_label?: string;
  }): Promise<string | null> {
    const workspaceId = currentWorkspace.value?.workspace_id;
    const employeeId = employee.employee_id?.trim();
    if (!workspaceId || !employeeId) {
      return null;
    }

    const title = employeeIdeThreadTitle(employee);

    try {
      await loadIdeThreads(workspaceId);
      const existing = (ideThreadsByWorkspaceId.value[workspaceId] ?? []).find(
        (thread) => (thread.employee_id ?? '').trim() === employeeId,
      );
      if (existing?.thread_id) {
        flushIdeComposerDraft();
        // Continuous-worker / fan-out writes the teammate thread out-of-band — always
        // refetch so AgentDock does not show a stale pre-shift cache.
        await selectIdeThread(existing.thread_id, { forceRefresh: true });
        openIdeComposer({ keepActivityView: true });
        return existing.thread_id;
      }

      const created = await createWorkspaceChatThread(workspaceId, {
        surface: 'ide',
        title,
        employeeId,
        employeeRole: employee.role,
      });
      ideThreadsByWorkspaceId.value = {
        ...ideThreadsByWorkspaceId.value,
        [workspaceId]: sortIdeThreadsNewestFirst([
          created,
          ...(ideThreadsByWorkspaceId.value[workspaceId] ?? []).filter(
            (thread) => thread.thread_id !== created.thread_id,
          ),
        ]),
      };
      flushIdeComposerDraft();
      await selectIdeThread(created.thread_id, { forceRefresh: true });
      ideComposerDraft.value = '';
      persistIdeComposerDraft(workspaceId, '', created.thread_id);
      openIdeComposer({ keepActivityView: true });
      return created.thread_id;
    } catch (error) {
      commandMutationError.value =
        error instanceof Error ? error.message : 'Failed to open teammate chat';
      return null;
    }
  }

  async function selectIdeThread(
    threadId: string,
    options?: { forceRefresh?: boolean },
  ): Promise<void> {
    const workspaceId = currentWorkspace.value?.workspace_id;
    if (!workspaceId) {
      return;
    }

    const forceRefresh = options?.forceRefresh === true;
    const previousThreadId = activeIdeThreadId.value;
    if (previousThreadId === threadId && !forceRefresh) {
      ensureIdeThreadTabOpen(threadId);
      return;
    }

    if (previousThreadId && previousThreadId !== threadId) {
      flushIdeComposerDraft();
      // Keep the previous thread's live SSE + message cache — do not disconnect.
      workspaceIdeThreadMessagesById.value = {
        ...workspaceIdeThreadMessagesById.value,
        [previousThreadId]: [...threadMessages.value],
      };
    }

    setWorkspaceSurfaceThreadId(workspaceId, 'ide', threadId);
    activeThreadId.value = threadId;
    ideStreamFocusThreadId.value = threadId;
    ensureIdeThreadTabOpen(threadId);
    syncIdeComposerDraftForThread(workspaceId, threadId);

    // Focus this thread's stream chrome (or clear globals if it is idle).
    applyWorkspaceStreamUiToGlobals(threadId);
    if (!getWorkspaceStreamUi(threadId).active) {
      agentStreamActive.value = false;
      agentStreamMessageId.value = null;
      ideComposerActivity.value = null;
      // Keep ideAgentRunId from stream UI defaults (null when idle).
      ideAgentRunId.value = getWorkspaceStreamUi(threadId).ideAgentRunId;
    }

    if (forceRefresh) {
      const nextCache = { ...workspaceIdeThreadMessagesById.value };
      delete nextCache[threadId];
      workspaceIdeThreadMessagesById.value = nextCache;
    } else {
      const cached = workspaceIdeThreadMessagesById.value[threadId];
      if (cached?.length) {
        threadMessages.value = cached;
        commandMutationState.value = 'idle';
        commandMutationError.value = null;
        return;
      }
    }

    if (layoutMode.value === 'ide') {
      threadMessages.value = [];
      commandMutationState.value = 'idle';
      commandMutationError.value = null;
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
      const uiAction = parseChatUiAction(response.ui_action);
      if (uiAction) {
        applyChatUiAction(
          {
            setCurrentWorkspace,
            openWorkspaceFile,
            setLayoutMode,
            setVoiceOrbDock,
            requestVoiceOrbSmartDodge,
          },
          uiAction,
        );
      }
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

  const {
    handoffDiscussedSignalToIde,
    handoffMutationError,
    handoffMutationState,
    handoffSignalToIde,
    lastDiscussedSignal,
    pendingHandoffDismissSignalId,
    routeTaskToEmployee,
  } = createSignalHandoffSlice({
    currentWorkspace,
    workspaces,
    operatorBriefing,
    ideComposerDraft,
    activeIdeThreadId,
    activeIdeEmployeeRecord,
    companyEmployeesForCurrentWorkspace,
    setCurrentWorkspace,
    setLayoutMode,
    hydrateWorkspaceIdeChat,
    loadCompanyEmployees,
    openOrFocusEmployeeIdeThread,
    selectIdeThread,
    createIdeThread,
    submitIdeComposer,
  });

  function restoreComposerDraft(content: string): void {
    const trimmed = content.trim();
    commandMutationError.value = null;
    if (layoutMode.value === 'operator') {
      operatorCommandDraft.value = trimmed;
      setDockHeroMode('command');
      commandFocusToken.value += 1;
      return;
    }
    openIdeComposerWithDraft(trimmed, { keepActivityView: false });
  }

  const {
    focusAttentionSidebar,
    closeIdeAttentionPanel,
    closeIdeBriefingPanel,
    openIdeBriefingPanel,
    toggleSignalDetails,
    focusMissionControl,
    focusOperatorTaskBoard,
    focusWatchConnectors,
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
    connectorsEmphasized,
    briefingSeamEmphasized,
    operatorCenterView,
    dockHeroMode,
    expandedDockSeams,
    dockThreadSeamTouched,
    setLeftSidebarMode,
    setDockHeroMode,
    restoreComposerDraft,
    setLayoutMode,
  });

  const {
    kairoSpeechSessionId,
    voiceDeliveryAllowed,
    stopKairoSpeech,
    pauseKairoSpeech,
    resumeKairoSpeech,
    interruptKairoVoice,
    speakKairoConversationLine,
    handleKairoPresenceAction,
    deliverKairoSpokenAlert,
    speakOperatorBriefing,
    maybeSpeakBootGreeting,
    kairoVoiceContext,
  } = createKairoVoiceSlice({
    currentWorkspace,
    operatorPresenceSettings,
    operatorBriefing,
    runtimeSummary,
    layoutMode,
    pendingApprovalsCount,
    kairoSpeechQueueActive,
    kairoVoiceEngineActive,
    kairoVoicePaused,
    ideComposerActivity,
    activeWorkspaceFilePath,
    workspaces,
    effectiveKairoNarrationLevel,
    kairoPresenceState,
    briefingVoiceTranscript,
    getWorkspaceSurfaceThreadId,
    currentThreadSurface,
    focusAttentionSidebar,
    focusKairoBriefing,
    focusCommandSeam,
  });

  function attachChatStream(
    workspaceId: string,
    threadId: string,
    messageId: string,
    options?: {
      activity?: IdeComposerActivity | null;
      ideAgentRunId?: string | null;
      /** Seed this thread's cache (background follow). Prefer over copying the focused transcript. */
      seedMessages?: OperatorThreadEntry[];
      /** Keep an existing cache entry instead of overwriting from the focused transcript. */
      preserveMessageCache?: boolean;
    },
  ): void {
    const streamActivity = options?.activity !== undefined ? options.activity : ideComposerActivity.value;
    const streamRunId =
      options?.ideAgentRunId !== undefined ? options.ideAgentRunId : ideAgentRunId.value;
    const attachedRunId = streamRunId;
    // Only replace this thread's session — leave sibling teammate streams running.
    disconnectChatStreamSession(threadId);
    setWorkspaceStreamUi(threadId, {
      active: true,
      messageId,
      activity: streamActivity,
      ideAgentRunId: streamRunId,
    });
    if (options?.seedMessages) {
      workspaceIdeThreadMessagesById.value = {
        ...workspaceIdeThreadMessagesById.value,
        [threadId]: [...options.seedMessages],
      };
    } else if (!options?.preserveMessageCache) {
      workspaceIdeThreadMessagesById.value = {
        ...workspaceIdeThreadMessagesById.value,
        [threadId]: [...threadMessages.value],
      };
    }
    const composerMode = streamActivity?.mode;
    const fullAccessNarration = streamActivity?.executionAccess === 'full';
    const operatorPrompt = streamActivity?.operatorPrompt?.trim() ?? '';
    let streamedContent = '';
    let terminalAutoRevealSeen = false;
    const streamIncremental = createAgentStreamIncrementalState({
      personaName: activeIdeEmployee.value?.name ?? null,
    });
    const streamUiBatcher = createRafStreamUiBatcher<Partial<WorkspaceStreamUiState>>(
      (streamThreadId, partial) => setWorkspaceStreamUi(streamThreadId, partial),
    );
    const contentBatcher = createStreamMessageContentBatcher(patchThreadMessageContent);
    const settleStreamUi = (clearRunId = false) => {
      streamUiBatcher.flushNow(threadId);
      contentBatcher.flushNow(threadId);
      setWorkspaceStreamUi(threadId, {
        active: false,
        messageId: null,
        activity: null,
        ...(clearRunId ? { ideAgentRunId: null } : {}),
      });
      streamUiBatcher.cancel(threadId);
      contentBatcher.cancel(threadId);
      disconnectChatStreamSession(threadId);
      void refreshRunSurfaces().finally(() => {
        void flushIdeComposerQueueIfIdle();
      });
      // Refresh roster immediately so failure banners clear when the backend
      // already shows the latest completed outcome (do not wait for the 20s poll).
      if (workspaceId) {
        void loadCompanyEmployees(workspaceId);
      }
    };
    const voiceContext = kairoVoiceContext();
    const voiceNarration = createAgentStreamVoiceSession({
      composerMode,
      messageId,
      sessionId: kairoSpeechSessionId,
      workspaceId: () => workspaceId,
      narration: () => effectiveKairoNarrationLevel.value,
      operatorPresenceSettings: () => operatorPresenceSettings.value,
      voiceDeliveryAllowed: () =>
        voiceDeliveryAllowed() && ideStreamFocusThreadId.value === threadId,
      operatorPrompt: () => operatorPrompt,
      fullAccess: () => voiceContext.fullAccess,
      layoutMode: () => layoutMode.value,
      idePresenceProfile: () => idePresenceProfile.value,
      azureVoiceId: () => activeIdeEmployee.value?.azure_voice_id ?? null,
      speaker: () => {
        const employee = activeIdeEmployee.value;
        return employee ? employeeVoiceSpeaker(employee) : null;
      },
    });
    chatStreamSessionsByWorkspace.set(
      threadId,
      startChatStreamSession({
        threadId,
        messageId,
        onDelta: (content) => {
          streamedContent = content;
          contentBatcher.schedule(threadId, { messageId, content });
          const activity = getWorkspaceStreamUi(threadId).activity as IdeComposerActivity | null;
          handleAgentStreamVoiceDelta({
            voiceNarration,
            streamIncremental,
            content,
            fullAccessNarration,
            patchActivity: (activityView) => {
              if (!activity) {
                return;
              }
              streamUiBatcher.schedule(threadId, {
                activity: {
                  ...activity,
                  label: activityView.label,
                  liveBodyFull: activityView.liveBodyFull,
                  liveBodySpoken: activityView.liveBodySpoken,
                  liveBodyTruncated: activityView.liveBodyTruncated,
                  streamCounts: streamIncremental.toCounts(),
                },
              });
            },
          });
          if (
            !terminalAutoRevealSeen &&
            streamIncremental.toCounts().terminal > 0 &&
            ideStreamFocusThreadId.value === threadId
          ) {
            terminalAutoRevealSeen = true;
            void backgroundIdeAgentRun();
          }
        },
        onMilestone: (payload) => {
          if (ideStreamFocusThreadId.value === threadId) {
            voiceNarration.narrateProgress(payload);
          }
        },
        onDone: (payload) => {
          try {
            contentBatcher.flushNow(threadId);
            clearIdeRunRecovery(attachedRunId ?? undefined);
            if (payload.system_message_id && payload.system_content) {
              patchThreadMessageContent(
                threadId,
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
                threadId,
                messageId,
                payload.content ?? streamedContent,
                streamAttachments,
              );
            }
            const uiAction = parseChatUiAction(payload.ui_action);
            if (uiAction && ideStreamFocusThreadId.value === threadId) {
              applyChatUiAction(
                {
                  setCurrentWorkspace,
                  openWorkspaceFile,
                  setLayoutMode,
                  setVoiceOrbDock,
                  requestVoiceOrbSmartDodge,
                },
                uiAction,
              );
            }
            const finalContent = payload.content ?? streamedContent;
            if (ideStreamFocusThreadId.value === threadId) {
              voiceNarration.narrateCompletion(finalContent);
            }
            if (
              currentWorkspace.value?.workspace_id === workspaceId &&
              ideStreamFocusThreadId.value === threadId
            ) {
              for (const path of editedFilePathsFromTranscript(finalContent)) {
                if (openedFilePaths.value.includes(path)) {
                  void reloadWorkspaceFile(path);
                }
              }
            }
          } finally {
            settleStreamUi(true);
          }
        },
        onError: (message, payload) => {
          if (ideStreamFocusThreadId.value === threadId) {
            voiceNarration.narrateFailure(streamedContent, message);
          }
          if (payload?.system_message_id && payload.system_content) {
            patchThreadMessageContent(
              threadId,
              payload.system_message_id,
              payload.system_content,
            );
          }
          if (
            currentWorkspace.value?.workspace_id === workspaceId &&
            ideStreamFocusThreadId.value === threadId
          ) {
            commandMutationError.value = message;
          }
          settleStreamUi();
        },
      }),
    );
  }

  createBusyEmployeeIdeStreamSlice({
    currentWorkspaceId: computed(() => currentWorkspace.value?.workspace_id ?? null),
    layoutMode,
    companyEmployees: companyEmployeesForCurrentWorkspace,
    ideThreadsByWorkspaceId,
    workspaceIdeThreadMessagesById,
    loadIdeThreads,
    ensureIdeThreadTabOpen,
    getWorkspaceStreamUi,
    attachChatStream,
  });
  function clearIdeAgentRunLink(): void {
    ideAgentRunId.value = null;
  }
  function setIdeDebugModeSelected(selected: boolean): void {
    ideDebugModeSelected.value = selected;
  }

  function openIdeComposer(options: { keepActivityView?: boolean } = {}): void {
    openIdeComposerSurface({
      layoutMode: layoutMode.value, setLayoutMode, agentDockCollapsed,
      persistAgentDockCollapsed, ideActivityView, commandFocusToken, commandMutationError,
      keepActivityView: options.keepActivityView,
    });
  }

  function openIdeComposerWithDraft(content: string, options: { keepActivityView?: boolean } = {}): void {
    openIdeComposerSurfaceWithDraft({
      content, ideComposerDraft, layoutMode: layoutMode.value, setLayoutMode,
      agentDockCollapsed, persistAgentDockCollapsed, ideActivityView, commandFocusToken,
      commandMutationError, keepActivityView: options.keepActivityView,
    });
  }

  function syncIdeComposerDraftForWorkspace(workspaceId: string | null | undefined): void {
    const threadId =
      (workspaceId && getWorkspaceSurfaceThreadId(workspaceId, 'ide')) ||
      activeIdeThreadId.value ||
      null;
    syncIdeComposerDraftForThread(workspaceId, threadId);
  }

  function syncIdeComposerDraftForThread(
    workspaceId: string | null | undefined,
    threadId: string | null | undefined,
  ): void {
    if (ideComposerDraftPersistTimer) {
      clearTimeout(ideComposerDraftPersistTimer);
      ideComposerDraftPersistTimer = null;
    }
    ideComposerDraft.value = readStoredIdeComposerDraft(workspaceId, threadId);
  }

  function flushIdeComposerDraft(): void {
    if (typeof window === 'undefined') {
      return;
    }
    if (ideComposerDraftPersistTimer) {
      clearTimeout(ideComposerDraftPersistTimer);
      ideComposerDraftPersistTimer = null;
    }
    const workspaceId = currentWorkspace.value?.workspace_id ?? null;
    if (!workspaceId) {
      return;
    }
    // Prefer thread scope; fall back to workspace so drafts survive before thread hydration.
    persistIdeComposerDraft(
      workspaceId,
      ideComposerDraft.value,
      activeIdeThreadId.value || null,
    );
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
      const workspaceId = currentWorkspace.value?.workspace_id ?? null;
      if (!workspaceId) {
        return;
      }
      persistIdeComposerDraft(
        workspaceId,
        ideComposerDraft.value,
        activeIdeThreadId.value || null,
      );
    }, 140);
  }

  watch(ideComposerDraft, () => {
    schedulePersistIdeComposerDraft();
  });

  function latestIdeOperatorPromptForRun(runId: string | null | undefined): string | null {
    const run = runs.value.find((record) => record.run_id === runId) ?? null;
    return resolveAgentContinuePrompt({
      runId: String(runId ?? ''),
      runSummary: run?.summary,
      ideMessages: threadMessages.value,
      operatorMessages: operatorThreadMessages.value,
    });
  }

  async function dispatchIdeComposerMessage(
    composerMode: IdeComposerMode,
    options: {
      contentOverride?: string;
      linkedRunIdOverride?: string | null;
      threadIdOverride?: string | null;
      recoveryCountOverride?: number;
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
      const linkedRunId = isRunLinkedComposerMode(composerMode)
        ? options.linkedRunIdOverride
          ?? resolveIdeAgentLinkedRunId(ideAgentRunId.value, runs.value, {
            expectedMode: composerMode,
          })
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
      let controlPlaneBootId = '';
      if (isRunLinkedComposerMode(composerMode)) {
        try {
          controlPlaneBootId = await fetchControlPlaneBootId();
        } catch {
          // Recovery remains manual when the boot identity cannot be captured.
        }
      }
      const response = await postChatMessage({
        workspace_id: workspaceId,
        content,
        thread_id:
          options.threadIdOverride ?? getWorkspaceSurfaceThreadId(workspaceId, 'ide'),
        run_id: linkedRunId,
        composer_mode: composerMode,
        active_file_path: activeWorkspaceFilePath.value,
        editor_selection: contextPayload.editor_selection,
        terminal_snippet: contextPayload.terminal_snippet,
        attachment_ids: attachmentIds.length ? attachmentIds : undefined,
        runtime_target: selectedRuntimeTargetId.value || null,
        runtime_model: selectedComposerModel.value || null,
        execution_access: isToolCapableComposerMode(composerMode)
          ? agentExecutionAccess.value
          : undefined,
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
      if (isRunLinkedComposerMode(composerMode) && response.run_id) {
        ideAgentRunId.value = response.run_id;
      }
      const uiAction = parseChatUiAction(response.ui_action);
      if (uiAction) {
        applyChatUiAction(
          {
            setCurrentWorkspace,
            openWorkspaceFile,
            setVoiceOrbDock,
            requestVoiceOrbSmartDodge,
          },
          uiAction,
        );
      }
      if (response.streaming && response.stream_agent_message_id) {
        commandMutationState.value = 'idle';
        if (response.agent_terminal_session) {
          applyAgentTerminalSession(response.agent_terminal_session);
        }
        ideComposerActivity.value = {
          label: buildIdeStreamActivityLabel(agentExecutionAccess.value, composerMode),
          mode: composerMode,
          executionAccess: agentExecutionAccess.value,
          operatorPrompt: content,
        };
        if (
          response.run_id &&
          controlPlaneBootId &&
          isRunLinkedComposerMode(composerMode)
        ) {
          persistIdeRunRecovery({
            workspaceId,
            threadId: response.thread_id,
            runId: response.run_id,
            mode: composerMode === 'plan' ? 'plan' : composerMode === 'debug' ? 'debug' : 'agent',
            controlPlaneBootId,
            recoveryCount: options.recoveryCountOverride ?? 0,
          });
        }
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
    composerMode: IdeComposerMode,
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
    composerMode: IdeComposerMode,
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
    syncCurrentWorkspace,
    loadWorkspaces,
    loadRuns,
    loadRunHistory,
    registerWorkspace,
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
    // Operator entry keeps the persisted center view (default: Mission Control fleet).
    if (mode === 'ide') {
      // Quiet IDE: restore persisted collapse (default collapsed). Operator galaxy CSS
      // only hides the right dock in Operator mode, so IDE entry no longer force-expands.
      agentDockCollapsed.value = readStoredAgentDockCollapsed();
    }
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
    focusIdeSidebarView,
    setIdeActivityView,
    toggleIdeExplorer,
    toggleAgentDock,
    revealTeamRosterForActiveEmployee,
  } = createIdeWorkbenchChromeSlice({
    ideTerminalRevealToken,
    ideTerminalToggleToken,
    teamRosterRevealToken,
    ideActivityView,
    ideExplorerCollapsed,
    agentDockCollapsed,
    ideAttentionPanelOpen,
    ideBriefingPanelOpen,
  });

  function syncWorkbenchTerminalPanelVisible(visible: boolean): void {
    workbenchTerminalPanelVisible.value = visible;
  }

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
    runCommandInAgentBackgroundTerminal,
    runCommandInOperatorTerminal,
    setActiveTerminalSession,
    splitTerminalSession,
  } = terminalSessionStore;

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

    if (isBinaryFilePath(path)) {
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

    if (isBinaryFilePath(path)) {
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
    readOnly?: boolean;
    planId?: string;
  }): string | null {
    const title = formatAgentDraftTitle(options.title.trim() || 'Agent response');
    const content = options.content.trim();
    if (!content) {
      return null;
    }
    const { drafts, id } = upsertAgentDraftDocument({
      drafts: draftDocuments.value,
      title,
      content,
      readOnly: options.readOnly === true,
      planId: options.planId?.trim() || undefined,
      idFactory: (slug) => `draft:agent-${slug}-${Date.now().toString(36)}`,
    });
    draftDocuments.value = drafts;
    if (options.focus !== false) {
      activeEditorDocumentId.value = id;
    }
    if (options.preferPreview !== false) {
      persistEditorMarkdownPreviewEnabled(id, true);
    }
    return id;
  }

  const { openImageInCanvas, openAgentEditReview } = createShellAgentCanvasOps({
    layoutMode,
    setLayoutMode,
    currentWorkspace,
    draftDocuments,
    openedFilePaths,
    activeEditorDocumentId,
    openWorkspaceFile,
    ensureWorkspaceFileLoaded,
  });

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
      // Persist outgoing composer draft while currentWorkspace is still the old one.
      flushIdeComposerDraft();
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
      void loadRunHistory(
        resolveRunHistoryRunId(
          runs.value.filter((run) => run.workspace_id === workspaceId),
          ideAgentRunId.value,
        ),
      );
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
    watchConnected: () => Boolean(runtimeSummary.value?.watch.connected),
    loadRuntimeSummary: () => loadRuntimeSummary(),
    loadInbox: () => loadInbox(),
    loadOperatorBriefing: () => loadOperatorBriefing(),
    loadOperatorFleetHealth: () => loadOperatorFleetHealth(),
  });

  async function testKairoVoiceFromSettings(options?: {
    speechRate?: number;
    speechPitch?: number;
  }): Promise<'azure' | 'browser' | 'skipped'> {
    if (
      operatorPresenceSettings.value.privacy_mode ||
      effectiveKairoNarrationLevel.value === 'off'
    ) {
      return 'skipped';
    }
    setKairoConversationPhase('speaking');
    kairoVoicePaused.value = false;
    try {
      const result = await speakKairoLine(
        'Systems are up — voice delivery looks good from here.',
        {
          speechRate: options?.speechRate ?? operatorPresenceSettings.value.speech_rate,
          speechPitch: options?.speechPitch ?? operatorPresenceSettings.value.speech_pitch,
        },
      );
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
    voiceOrbDock,
    voiceOrbPosition,
    voiceOrbUserPinned,
    voiceOrbDragging,
    voiceOrbVisible,
    voiceOrbAnchorStyle,
    setVoiceOrbDock,
    setVoiceOrbPosition,
    resetVoiceOrbDock,
    setVoiceOrbVisible,
    hideVoiceOrb,
    showVoiceOrb,
    requestVoiceOrbSmartDodge,
    ensureVoiceOrbPosition,
    persistVoiceOrbPlacement,
  } = createVoiceOrbPlacementController();

  const {
    loadOperatorBriefing,
    refreshOperatorPresence,
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
    agentExecutionAccess,
    setAgentExecutionAccess,
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

  const { autoContinueInterruptedIdeRun } = createIdeRunAutoRecoverySlice({
    autoRunRecoveryInFlight,
    runs,
    agentStreamActive,
    commandMutationState,
    commandMutationError,
    currentWorkspace,
    ideAgentRunId,
    ideComposerActivity,
    agentExecutionAccess,
    workspaceIdeThreadMessagesById,
    activeThreadId,
    loadRuns,
    setWorkspaceSurfaceThreadId,
    loadWorkspaceThread,
    attachChatStream,
    dispatchIdeComposerMessage,
  });

  function clearStaleIdeStreamUi(): void {
    const runPhaseById: Record<string, string | undefined> = {};
    for (const run of runs.value) {
      runPhaseById[run.run_id] = run.phase;
    }
    const staleThreadIds = listStaleIdeStreamThreadIds({
      streamUiByThreadId: workspaceStreamUiById.value,
      liveSessionThreadIds: chatStreamSessionsByWorkspace.keys(),
      runPhaseById,
      runsLoaded: runsLoadState.value === 'loaded',
    });
    if (!staleThreadIds.length) {
      return;
    }
    for (const threadId of staleThreadIds) {
      disconnectChatStreamSession(threadId);
      setWorkspaceStreamUi(threadId, {
        active: false,
        messageId: null,
        activity: null,
        ideAgentRunId: null,
      });
    }
  }

  async function refreshRunSurfaces(options?: { light?: boolean; forceFull?: boolean }): Promise<void> {
    // During an active stream/run, full surface refresh (CLI status + briefing +
    // fleet + brain) routinely takes 5–8s and trips Chrome "Page Unresponsive".
    const activeBusy =
      agentStreamActive.value ||
      primaryActiveRun.value?.phase === 'executing' ||
      primaryActiveRun.value?.phase === 'planning' ||
      primaryActiveRun.value?.phase === 'starting' ||
      primaryActiveRun.value?.phase === 'queued';
    const light =
      options?.forceFull === true
        ? false
        : options?.light === true || activeBusy;
    if (light) {
      // Live SSE ticks must stay cheap: skip CLI status/summary AND watch inbox
      // (inbox watch probe regularly hits a ~5s timeout and freezes the console).
      await loadRuns({ sync: false });
      clearStaleIdeStreamUi();
      await autoContinueInterruptedIdeRun();
      await flushIdeComposerQueueIfIdle();
      return;
    }
    const briefingBackground = briefingLoadState.value === 'loaded';
    const runtimeBackground = runtimeSummaryLoadState.value === 'loaded';
    const inboxBackground = inboxLoadState.value === 'loaded';
    // Soft full refresh: when surfaces are already loaded, only refresh runs +
    // inbox + history. Avoid stacking cold CLI/briefing probes on every mutation.
    if (
      briefingBackground &&
      runtimeBackground &&
      inboxBackground &&
      runtimeStatusLoadState.value === 'loaded'
    ) {
      await Promise.all([
        loadRuns({ sync: false }),
        loadInbox({ background: true }),
      ]);
      clearStaleIdeStreamUi();
      await loadRunHistory(
        resolveRunHistoryRunId(workspaceRuns.value, ideAgentRunId.value),
      );
      await autoContinueInterruptedIdeRun();
      await flushIdeComposerQueueIfIdle();
      return;
    }
    await Promise.all([
      loadRuns(),
      loadRuntimeStatus(),
      loadRuntimeSummary({ background: runtimeBackground }),
      loadInbox({ background: inboxBackground }),
      loadConnectors({ background: connectorsLoadState.value === 'loaded' }),
      loadOperatorBriefing({ background: briefingBackground }),
      loadOperatorFleetHealth({ background: operatorFleetHealthLoadState.value === 'loaded' }),
      operatorBrainGraphLoadState.value === 'loaded'
        ? loadOperatorBrainGraph({ background: true })
        : Promise.resolve(),
    ]);
    clearStaleIdeStreamUi();
    await loadRunHistory(
      resolveRunHistoryRunId(workspaceRuns.value, ideAgentRunId.value),
    );
    await autoContinueInterruptedIdeRun();
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
    const threadId = activeIdeThreadId.value ?? activeThreadId.value;
    runMutationState.value = 'stopping';
    runMutationError.value = null;
    if (threadId) {
      disconnectChatStreamSession(threadId);
      setWorkspaceStreamUi(threadId, {
        active: false,
        messageId: null,
        activity: null,
        ideAgentRunId: null,
      });
    }
    agentStreamActive.value = false;
    agentStreamMessageId.value = null;
    ideComposerActivity.value = null;

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
    if (!run || runMutationPending.value) {
      return;
    }
    const idleContinue =
      run.phase === 'executing' &&
      !agentStreamActive.value &&
      isToolCapableComposerMode(run.mode);
    if (!run.can_resume && !idleContinue) {
      return;
    }

    // Agent/Debug runs: CONTINUE/RESUME must re-dispatch work. Bare stop→resume only
    // flips phase and does not restart the agent (verified against live API).
    if (isToolCapableComposerMode(run.mode)) {
      ideAgentRunId.value = run.run_id;
      await resumeIdeAgentRun();
      return;
    }

    if (!run.can_resume) {
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
    const run = ideAgentLinkedRun.value ?? primaryActiveRun.value;
    if (!run || runMutationPending.value) {
      return;
    }
    if (isToolCapableComposerMode(run.mode)) {
      ideAgentRunId.value = run.run_id;
    }
    const linked = ideAgentLinkedRun.value ?? run;
    const idleContinue =
      linked.phase === 'executing' &&
      !agentStreamActive.value &&
      isToolCapableComposerMode(linked.mode);
    if (!linked.can_resume && !idleContinue) {
      return;
    }

    runMutationState.value = 'resuming';
    runMutationError.value = null;

    try {
      const latestPrompt = latestIdeOperatorPromptForRun(linked.run_id);
      if (!latestPrompt) {
        runMutationError.value =
          'Continue failed: no operator prompt found for this run. Type a follow-up in the IDE composer.';
        return;
      }

      const resumeMode: IdeComposerMode =
        linked.mode === 'debug' ? 'debug' : 'agent';
      const dispatched = await dispatchIdeComposerMessage(resumeMode, {
        contentOverride: latestPrompt,
        linkedRunIdOverride: linked.run_id,
        clearDraftOnSuccess: false,
      });
      if (dispatched) {
        await refreshRunSurfaces();
        afterRunLifecycleMutation();
        return;
      }

      runMutationError.value =
        commandMutationError.value ||
        'Continue failed: agent re-dispatch did not start. Check Full Access and try again.';
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

    // Warm CLI status once before parallel summary/briefing/fleet so they hit
    // the snapshot cache instead of stacking multi-second auth probes.
    await loadRuntimeStatus();
    await Promise.all([
      loadRuntimeSummary({ background: true }),
      loadInbox({ background: true }),
      loadConnectors(),
      // Light briefing keeps first paint under ~100ms; full briefing fills signals
      // in the background without blocking bootstrap_complete.
      loadOperatorBriefing({ background: true, light: true }),
      loadOperatorFleetHealth({ background: true }),
    ]);
    void loadOperatorBriefing({ background: true });
    await loadRunHistory(
      resolveRunHistoryRunId(workspaceRuns.value, ideAgentRunId.value),
    );
    if (workspaceId) {
      await loadWorkspaceThread(workspaceId, 'operator');
      await hydrateWorkspaceIdeChat(workspaceId);
      if (layoutMode.value === 'operator') {
        threadMessages.value = operatorThreadMessages.value;
      }
    }
    await autoContinueInterruptedIdeRun();
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
    connectorsEmphasized,
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
    ideDebugModeSelected,
    activeIdeThreadId,
    activeIdeThread,
    activeIdeEmployee,
    activeIdeEmployeeRecord,
    activeIdeEmployeeFailureLine,
    activeIdeEmployeeShiftInterrupted,
    companyEmployeesByWorkspaceId,
    companyEmployeesForCurrentWorkspace,
    companyEmployeesFleet,
    loadCompanyEmployees,
    workspaceTasksById,
    workspaceTasksForCurrentWorkspace: workspaceTasksWithPlanLinks,
    workspaceTasksError,
    workspaceTasksMutating,
    loadWorkspaceTasks,
    createCurrentWorkspaceTask,
    cancelCurrentWorkspaceTask,
    leadPlansByWorkspaceId,
    leadPlansForCurrentWorkspace,
    leadPlanIdByTaskId,
    leadPlansError,
    leadPlansMutating,
    loadLeadPlans,
    fanOutCurrentWorkspaceLeadPlan,
    synthesizeCurrentLeadPlan,
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
    streamingIdeThreadIds,
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
    workbenchTerminalPanelVisible,
    syncWorkbenchTerminalPanelVisible,
    teamRosterRevealToken,
    revealTeamRosterForActiveEmployee,
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
    setIdeDebugModeSelected,
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
    refreshOperatorThreadMessages,
    loadIdeThreads,
    hydrateWorkspaceIdeChat,
    createIdeThread,
    openOrFocusEmployeeIdeThread,
    selectIdeThread,
    closeIdeThreadTab,
    loadTerminalSessions,
    setActiveTerminalSession,
    createTerminalSession,
    createVaxonTerminalSession,
    backgroundIdeAgentRun,
    runCommandInAgentBackgroundTerminal,
    runCommandInOperatorTerminal,
    splitTerminalSession,
    renameTerminalSession,
    closeTerminalSession,
    loadWorkspaces,
    registerWorkspace,
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
    runSeamDisplayRun,
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
    toggleIdeTerminalPanel,
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
    focusIdeSidebarView,
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
    routeTaskToEmployee,
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
    openIdeComposer,
    openIdeComposerWithDraft,
    focusAttentionSidebar,
    focusMissionControl,
    focusOperatorTaskBoard,
    focusWatchConnectors,
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
    openImageInCanvas,
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
    voiceOrbDock,
    voiceOrbPosition,
    voiceOrbUserPinned,
    voiceOrbDragging,
    voiceOrbVisible,
    voiceOrbAnchorStyle,
    setVoiceOrbDock,
    setVoiceOrbPosition,
    resetVoiceOrbDock,
    setVoiceOrbVisible,
    hideVoiceOrb,
    showVoiceOrb,
    requestVoiceOrbSmartDodge,
    ensureVoiceOrbPosition,
    persistVoiceOrbPlacement,
  };
});
