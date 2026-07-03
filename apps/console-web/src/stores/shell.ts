import { computed, ref } from 'vue';
import { defineStore } from 'pinia';

import { fetchInbox, fetchRuns, fetchRuntimeSummary } from '../api/control-plane';
import type {
  ApprovalRecord,
  InboxItem,
  RunRecord,
  RuntimeSummary,
  SignalView,
  ThreadMessage,
  WorkspaceRecord,
} from '../contracts/canonical';

export type LayoutMode = 'operator' | 'ide';
export type RuntimeSummaryLoadState = 'idle' | 'loading' | 'loaded' | 'error';
export type InboxLoadState = 'idle' | 'loading' | 'loaded' | 'error';
export type RunsLoadState = 'idle' | 'loading' | 'loaded' | 'error';
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
  const runtimeSummary = ref<RuntimeSummary | null>(null);
  const runtimeSummaryLoadState = ref<RuntimeSummaryLoadState>('idle');
  const runtimeSummaryError = ref<string | null>(null);
  const activeRun = ref<RunRecord | null>(null);
  const runs = ref<RunRecord[]>([]);
  const runsLoadState = ref<RunsLoadState>('idle');
  const runsError = ref<string | null>(null);
  const approvals = ref<ApprovalRecord[]>([]);
  const inboxItems = ref<InboxItem[]>([]);
  const inboxLoadState = ref<InboxLoadState>('idle');
  const inboxError = ref<string | null>(null);
  const signalViews = ref<SignalView[]>([]);
  const threadMessages = ref<ThreadMessage[]>([]);

  // UI shell scaffolding is local and intentionally placeholder-only.
  const editorTabs = ref<EditorTabDescriptor[]>(DEFAULT_EDITOR_TABS);
  const activeEditorTabId = ref<string>(DEFAULT_EDITOR_TABS[0].id);
  const terminalSessions = ref<TerminalSessionDescriptor[]>(DEFAULT_TERMINAL_SESSIONS);
  const activeTerminalSessionId = ref<string>(DEFAULT_TERMINAL_SESSIONS[0].id);
  const dockContext = ref<DockContextDescriptor>(DEFAULT_DOCK_CONTEXT);

  const layoutModeLabel = computed(() =>
    layoutMode.value === 'operator' ? 'Operator mode emphasis' : 'IDE mode emphasis',
  );

  const workspaceStateLabel = computed(() =>
    currentWorkspace.value ? 'WorkspaceRecord attached' : 'Awaiting WorkspaceRecord',
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
      return 'Awaiting RunRecord';
    }

    const run = activeRun.value;
    return `${run.run_id} · ${run.phase} · ${run.status} · ${run.summary}`;
  });

  const primaryActiveRun = computed(() => activeRun.value);

  const inboxStateLabel = computed(() => {
    if (inboxLoadState.value === 'loading') {
      return 'Loading inbox signal';
    }

    if (inboxLoadState.value === 'error') {
      return 'Inbox signal unavailable';
    }

    const primary = inboxItems.value[0];
    if (!primary) {
      return 'Awaiting InboxItem / SignalView';
    }

    return `${primary.signal_id} · ${primary.severity} · ${primary.status} · ${primary.source}`;
  });

  const primaryInboxItem = computed(() => inboxItems.value[0] ?? null);

  const approvalStateLabel = computed(() =>
    approvals.value.length > 0 ? 'ApprovalRecord attached' : 'Awaiting ApprovalRecord',
  );

  const threadStateLabel = computed(() =>
    threadMessages.value.length > 0 ? 'ThreadMessage attached' : 'Awaiting ThreadMessage',
  );

  function setLayoutMode(mode: LayoutMode): void {
    layoutMode.value = mode;
  }

  function setActiveEditorTab(id: string): void {
    activeEditorTabId.value = id;
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

  async function loadRuns(): Promise<void> {
    runsLoadState.value = 'loading';
    runsError.value = null;

    try {
      const snapshot = await fetchRuns();
      runs.value = snapshot.items;
      activeRun.value =
        snapshot.items.find((run) => run.phase !== 'completed' && run.phase !== 'failed' && run.phase !== 'cancelled') ??
        snapshot.items[0] ??
        null;
      runsLoadState.value = 'loaded';
    } catch (error) {
      runsLoadState.value = 'error';
      runsError.value = error instanceof Error ? error.message : 'runs request failed';
    }
  }

  async function loadBootstrapData(): Promise<void> {
    await Promise.all([loadRuntimeSummary(), loadInbox(), loadRuns()]);
  }

  return {
    activeEditorTabId,
    activeRun,
    activeTerminalSessionId,
    approvals,
    approvalStateLabel,
    currentWorkspace,
    dockContext,
    editorTabs,
    inboxError,
    inboxItems,
    inboxLoadState,
    inboxStateLabel,
    layoutMode,
    layoutModeLabel,
    loadBootstrapData,
    loadInbox,
    loadRuns,
    loadRuntimeSummary,
    primaryActiveRun,
    primaryInboxItem,
    runs,
    runsError,
    runsLoadState,
    runStateLabel,
    runtimeStateLabel,
    runtimeSummary,
    runtimeSummaryError,
    runtimeSummaryLoadState,
    setActiveEditorTab,
    setLayoutMode,
    signalViews,
    terminalSessions,
    threadMessages,
    threadStateLabel,
    workspaces,
    workspaceStateLabel,
  };
});
