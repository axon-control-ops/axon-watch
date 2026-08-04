import type { ComputedRef, Ref } from 'vue';

import type { RunRecord, WorkspaceRecord } from '../../../contracts/canonical';
import type { ChatStreamSession } from '../../../lib/chat-stream-session';
import {
  listReattachIdeStreamThreadIds,
  listStaleIdeStreamThreadIds,
} from '../../../lib/stale-ide-stream-ui';
import type { WorkspaceStreamUiState } from '../../../lib/workspace-stream-ui';
import { resolveRunHistoryRunId } from '../../shell-run-selection';
import type {
  BriefingLoadState,
  InboxLoadState,
  RunsLoadState,
  RuntimeStatusLoadState,
  RuntimeSummaryLoadState,
} from '../types';

interface CreateRunSurfacesRefreshSliceInput {
  runs: Ref<RunRecord[]>;
  workspaceStreamUiById: Ref<Record<string, WorkspaceStreamUiState>>;
  chatStreamSessionsByWorkspace: Map<string, ChatStreamSession>;
  runsLoadState: Ref<RunsLoadState>;
  currentWorkspace: Ref<WorkspaceRecord | null>;
  ideThreadsByWorkspaceId: Ref<
    Record<string, Array<{ thread_id: string }>>
  >;
  getWorkspaceSurfaceThreadId: (
    workspaceId: string,
    surface: 'ide',
  ) => string | null;
  reattachIdeChatStream: (threadId: string, workspaceId: string) => Promise<void>;
  disconnectChatStreamSession: (threadId: string) => void;
  setWorkspaceStreamUi: (
    threadId: string,
    ui: Partial<WorkspaceStreamUiState>,
  ) => void;
  agentStreamActive: Ref<boolean>;
  primaryActiveRun: ComputedRef<RunRecord | null>;
  loadRuns: (options?: { sync?: boolean }) => Promise<void>;
  autoContinueInterruptedIdeRun: () => Promise<void>;
  flushIdeComposerQueueIfIdle: () => Promise<void>;
  briefingLoadState: Ref<BriefingLoadState>;
  runtimeSummaryLoadState: Ref<RuntimeSummaryLoadState>;
  inboxLoadState: Ref<InboxLoadState>;
  runtimeStatusLoadState: Ref<RuntimeStatusLoadState>;
  loadInbox: (options?: { background?: boolean }) => Promise<void>;
  loadRunHistory: (runId: string | null) => Promise<void>;
  workspaceRuns: ComputedRef<RunRecord[]>;
  ideAgentRunId: Ref<string | null>;
  loadRuntimeStatus: () => Promise<void>;
  loadRuntimeSummary: (options?: { background?: boolean }) => Promise<void>;
  loadConnectors: (options?: { background?: boolean }) => Promise<void>;
  connectorsLoadState: Ref<'idle' | 'loading' | 'loaded' | 'error'>;
  loadOperatorBriefing: (options?: { background?: boolean }) => Promise<void>;
  loadOperatorFleetHealth: (options?: { background?: boolean }) => Promise<void>;
  operatorFleetHealthLoadState: Ref<'idle' | 'loading' | 'loaded' | 'error'>;
  operatorBrainGraphLoadState: Ref<'idle' | 'loading' | 'loaded' | 'error'>;
  loadOperatorBrainGraph: (options?: { background?: boolean }) => Promise<void>;
}

export function createRunSurfacesRefreshSlice(input: CreateRunSurfacesRefreshSliceInput) {
  function clearStaleIdeStreamUi(): void {
    const runPhaseById: Record<string, string | undefined> = {};
    for (const run of input.runs.value) {
      runPhaseById[run.run_id] = run.phase;
    }
    const decisionInput = {
      streamUiByThreadId: input.workspaceStreamUiById.value,
      liveSessionThreadIds: input.chatStreamSessionsByWorkspace.keys(),
      runPhaseById,
      runsLoaded: input.runsLoadState.value === 'loaded',
    };
    const reattachThreadIds = listReattachIdeStreamThreadIds(decisionInput);
    const staleThreadIds = listStaleIdeStreamThreadIds(decisionInput);
    const workspaceId = input.currentWorkspace.value?.workspace_id ?? null;
    const currentThreadIds = new Set(
      workspaceId
        ? (input.ideThreadsByWorkspaceId.value[workspaceId] ?? []).map(
            (thread) => thread.thread_id,
          )
        : [],
    );
    if (workspaceId) {
      const surfaceThreadId = input.getWorkspaceSurfaceThreadId(workspaceId, 'ide');
      if (surfaceThreadId) {
        currentThreadIds.add(surfaceThreadId);
      }
    }
    for (const threadId of reattachThreadIds) {
      if (workspaceId && currentThreadIds.has(threadId)) {
        void input.reattachIdeChatStream(threadId, workspaceId);
      }
    }
    if (!staleThreadIds.length) {
      return;
    }
    for (const threadId of staleThreadIds) {
      input.disconnectChatStreamSession(threadId);
      input.setWorkspaceStreamUi(threadId, {
        active: false,
        messageId: null,
        activity: null,
        ideAgentRunId: null,
      });
    }
  }

  async function refreshRunSurfaces(options?: {
    light?: boolean;
    forceFull?: boolean;
  }): Promise<void> {
    // During an active stream/run, full surface refresh (CLI status + briefing +
    // fleet + brain) routinely takes 5–8s and trips Chrome "Page Unresponsive".
    const activeBusy =
      input.agentStreamActive.value ||
      input.primaryActiveRun.value?.phase === 'executing' ||
      input.primaryActiveRun.value?.phase === 'planning' ||
      input.primaryActiveRun.value?.phase === 'starting' ||
      input.primaryActiveRun.value?.phase === 'queued';
    const light =
      options?.forceFull === true
        ? false
        : options?.light === true || activeBusy;
    if (light) {
      // Live SSE ticks must stay cheap: skip CLI status/summary AND watch inbox
      // (inbox watch probe regularly hits a ~5s timeout and freezes the console).
      await input.loadRuns({ sync: false });
      clearStaleIdeStreamUi();
      await input.autoContinueInterruptedIdeRun();
      await input.flushIdeComposerQueueIfIdle();
      return;
    }
    const briefingBackground = input.briefingLoadState.value === 'loaded';
    const runtimeBackground = input.runtimeSummaryLoadState.value === 'loaded';
    const inboxBackground = input.inboxLoadState.value === 'loaded';
    // Soft full refresh: when surfaces are already loaded, only refresh runs +
    // inbox + history. Avoid stacking cold CLI/briefing probes on every mutation.
    if (
      briefingBackground &&
      runtimeBackground &&
      inboxBackground &&
      input.runtimeStatusLoadState.value === 'loaded'
    ) {
      await Promise.all([
        input.loadRuns({ sync: false }),
        input.loadInbox({ background: true }),
      ]);
      clearStaleIdeStreamUi();
      await input.loadRunHistory(
        resolveRunHistoryRunId(input.workspaceRuns.value, input.ideAgentRunId.value),
      );
      await input.autoContinueInterruptedIdeRun();
      await input.flushIdeComposerQueueIfIdle();
      return;
    }
    await Promise.all([
      input.loadRuns(),
      input.loadRuntimeStatus(),
      input.loadRuntimeSummary({ background: runtimeBackground }),
      input.loadInbox({ background: inboxBackground }),
      input.loadConnectors({ background: input.connectorsLoadState.value === 'loaded' }),
      input.loadOperatorBriefing({ background: briefingBackground }),
      input.loadOperatorFleetHealth({
        background: input.operatorFleetHealthLoadState.value === 'loaded',
      }),
      input.operatorBrainGraphLoadState.value === 'loaded'
        ? input.loadOperatorBrainGraph({ background: true })
        : Promise.resolve(),
    ]);
    clearStaleIdeStreamUi();
    await input.loadRunHistory(
      resolveRunHistoryRunId(input.workspaceRuns.value, input.ideAgentRunId.value),
    );
    await input.autoContinueInterruptedIdeRun();
    await input.flushIdeComposerQueueIfIdle();
  }

  return { clearStaleIdeStreamUi, refreshRunSurfaces };
}
