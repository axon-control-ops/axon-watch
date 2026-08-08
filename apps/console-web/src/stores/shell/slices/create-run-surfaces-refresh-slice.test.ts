import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, ref } from 'vue';

import type { RunRecord, WorkspaceRecord } from '../../../contracts/canonical';
import type { ChatStreamSession } from '../../../lib/chat-stream-session';
import type { WorkspaceStreamUiState } from '../../../lib/workspace-stream-ui';
import { createRunSurfacesRefreshSlice } from './create-run-surfaces-refresh-slice';

function makeRun(phase: RunRecord['phase'], runId = 'run-1'): RunRecord {
  return {
    run_id: runId,
    workspace_id: 'ws-1',
    phase,
  } as RunRecord;
}

describe('createRunSurfacesRefreshSlice', () => {
  const loadRuns = vi.fn(async () => undefined);
  const autoContinueInterruptedIdeRun = vi.fn(async () => undefined);
  const flushIdeComposerQueueIfIdle = vi.fn(async () => undefined);
  const loadInbox = vi.fn(async () => undefined);
  const loadRunHistory = vi.fn(async () => undefined);
  const loadRuntimeStatus = vi.fn(async () => undefined);
  const loadRuntimeSummary = vi.fn(async () => undefined);
  const loadConnectors = vi.fn(async () => undefined);
  const loadOperatorBriefing = vi.fn(async () => undefined);
  const loadOperatorFleetHealth = vi.fn(async () => undefined);
  const loadOperatorBrainGraph = vi.fn(async () => undefined);
  const reattachIdeChatStream = vi.fn(async () => undefined);
  const disconnectChatStreamSession = vi.fn();
  const setWorkspaceStreamUi = vi.fn();
  const getWorkspaceSurfaceThreadId = vi.fn(() => null);

  const runs = ref<RunRecord[]>([]);
  const workspaceStreamUiById = ref<Record<string, WorkspaceStreamUiState>>({});
  const chatStreamSessionsByWorkspace = new Map<string, ChatStreamSession>();
  const runsLoadState = ref<'idle' | 'loading' | 'loaded' | 'error'>('loaded');
  const currentWorkspace = ref<WorkspaceRecord | null>({
    workspace_id: 'ws-1',
  } as WorkspaceRecord);
  const ideThreadsByWorkspaceId = ref<Record<string, Array<{ thread_id: string }>>>({
    'ws-1': [],
  });
  const agentStreamActive = ref(false);
  const primaryActiveRun = computed(() => runs.value[0] ?? null);
  const briefingLoadState = ref<'idle' | 'loading' | 'loaded' | 'error'>('loaded');
  const runtimeSummaryLoadState = ref<'idle' | 'loading' | 'loaded' | 'error'>('loaded');
  const inboxLoadState = ref<'idle' | 'loading' | 'loaded' | 'error'>('loaded');
  const runtimeStatusLoadState = ref<'idle' | 'loading' | 'loaded' | 'error'>('loaded');
  const workspaceRuns = computed(() => runs.value);
  const ideAgentRunId = ref<string | null>(null);
  const connectorsLoadState = ref<'idle' | 'loading' | 'loaded' | 'error'>('loaded');
  const operatorFleetHealthLoadState = ref<'idle' | 'loading' | 'loaded' | 'error'>('loaded');
  const operatorBrainGraphLoadState = ref<'idle' | 'loading' | 'loaded' | 'error'>('loaded');

  function createSlice() {
    return createRunSurfacesRefreshSlice({
      runs,
      workspaceStreamUiById,
      chatStreamSessionsByWorkspace,
      runsLoadState,
      currentWorkspace,
      ideThreadsByWorkspaceId,
      getWorkspaceSurfaceThreadId,
      reattachIdeChatStream,
      disconnectChatStreamSession,
      setWorkspaceStreamUi,
      agentStreamActive,
      primaryActiveRun,
      loadRuns,
      autoContinueInterruptedIdeRun,
      flushIdeComposerQueueIfIdle,
      briefingLoadState,
      runtimeSummaryLoadState,
      inboxLoadState,
      runtimeStatusLoadState,
      loadInbox,
      loadRunHistory,
      workspaceRuns,
      ideAgentRunId,
      loadRuntimeStatus,
      loadRuntimeSummary,
      loadConnectors,
      connectorsLoadState,
      loadOperatorBriefing,
      loadOperatorFleetHealth,
      operatorFleetHealthLoadState,
      operatorBrainGraphLoadState,
      loadOperatorBrainGraph,
    });
  }

  beforeEach(() => {
    vi.clearAllMocks();
    runs.value = [];
    agentStreamActive.value = false;
    briefingLoadState.value = 'loaded';
    runtimeSummaryLoadState.value = 'loaded';
    inboxLoadState.value = 'loaded';
    runtimeStatusLoadState.value = 'loaded';
    connectorsLoadState.value = 'loaded';
    operatorFleetHealthLoadState.value = 'loaded';
    operatorBrainGraphLoadState.value = 'loaded';
  });

  it('keeps light refresh cheap while a run is executing', async () => {
    runs.value = [makeRun('executing')];
    const { refreshRunSurfaces } = createSlice();

    await refreshRunSurfaces();

    expect(loadRuns).toHaveBeenCalledWith({ sync: false });
    expect(loadInbox).not.toHaveBeenCalled();
    expect(loadRuntimeStatus).not.toHaveBeenCalled();
    expect(autoContinueInterruptedIdeRun).toHaveBeenCalledOnce();
    expect(flushIdeComposerQueueIfIdle).toHaveBeenCalledOnce();
  });

  it('still refreshes runtime summary in the background during light refresh', async () => {
    // Regression: a light-only refresh loop (SSE ticks while a run is
    // executing, or the IDE-mode refresh path) must not leave watch
    // connectivity state stale forever — WATCH OFFLINE has to self-heal.
    runs.value = [makeRun('executing')];
    const { refreshRunSurfaces } = createSlice();

    await refreshRunSurfaces();

    expect(loadRuntimeSummary).toHaveBeenCalledWith({ background: true });
  });

  it('still refreshes runtime summary when light is forced explicitly', async () => {
    const { refreshRunSurfaces } = createSlice();

    await refreshRunSurfaces({ light: true });

    expect(loadRuntimeSummary).toHaveBeenCalledWith({ background: true });
    expect(loadRuntimeStatus).not.toHaveBeenCalled();
    expect(loadInbox).not.toHaveBeenCalled();
  });

  it('uses soft full refresh when core surfaces are already loaded', async () => {
    const { refreshRunSurfaces } = createSlice();

    await refreshRunSurfaces();

    expect(loadRuns).toHaveBeenCalledWith({ sync: false });
    expect(loadInbox).toHaveBeenCalledWith({ background: true });
    expect(loadRuntimeStatus).not.toHaveBeenCalled();
    expect(loadOperatorBriefing).not.toHaveBeenCalled();
    expect(loadRunHistory).toHaveBeenCalled();
  });

  it('runs a cold full refresh when surfaces are not loaded', async () => {
    briefingLoadState.value = 'idle';
    runtimeSummaryLoadState.value = 'idle';
    inboxLoadState.value = 'idle';
    runtimeStatusLoadState.value = 'idle';
    const { refreshRunSurfaces } = createSlice();

    await refreshRunSurfaces({ forceFull: true });

    expect(loadRuns).toHaveBeenCalled();
    expect(loadRuntimeStatus).toHaveBeenCalledOnce();
    expect(loadRuntimeSummary).toHaveBeenCalledOnce();
    expect(loadInbox).toHaveBeenCalledOnce();
    expect(loadConnectors).toHaveBeenCalledOnce();
    expect(loadOperatorBriefing).toHaveBeenCalledOnce();
    expect(loadOperatorFleetHealth).toHaveBeenCalledOnce();
  });
});
