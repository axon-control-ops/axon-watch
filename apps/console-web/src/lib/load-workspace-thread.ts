import {
  fetchThreadHistory,
  fetchWorkspaceChatThread,
  hasWorkspaceChatThread,
} from '../api/control-plane';
import { isApiNotFoundError, isApiTransientError } from '../api/client';
import type { ChatMessageRecord } from '../api/chat-api';
import type { OperatorThreadEntry } from './operator-thread';
import type { ThreadSurface } from './thread-surface-view';
import {
  buildWorkspaceThreadLoadKey,
  shouldApplyWorkspaceThreadLoad,
} from './workspace-thread-load';

export type LoadWorkspaceThreadDeps = {
  getSelectedThreadId: (workspaceId: string, surface: ThreadSurface) => string | null;
  setSelectedThreadId: (workspaceId: string, surface: ThreadSurface, threadId: string) => void;
  clearSelectedThreadId: (workspaceId: string, surface: ThreadSurface) => void;
  isViewingSurface: (workspaceId: string, surface: ThreadSurface) => boolean;
  isCurrentWorkspace: (workspaceId: string) => boolean;
  applyLoaded: (
    workspaceId: string,
    surface: ThreadSurface,
    loadedThreadId: string,
    mapped: OperatorThreadEntry[],
  ) => void;
  resetThreadContext: () => void;
  clearIdeAgentRunLink: () => void;
  setOperatorThreadEmpty: () => void;
  setLoadError: (message: string) => void;
  mapChatMessages: (items: ChatMessageRecord[]) => OperatorThreadEntry[];
  filterForSurface: (
    messages: OperatorThreadEntry[],
    surface: ThreadSurface,
  ) => OperatorThreadEntry[];
};

async function resolveThreadId(
  deps: LoadWorkspaceThreadDeps,
  workspaceId: string,
  surface: ThreadSurface,
  requestedThreadId?: string | null,
): Promise<string | null> {
  let threadId = requestedThreadId?.trim() || deps.getSelectedThreadId(workspaceId, surface);
  if (threadId) {
    return threadId;
  }

  const workspaceThread = await fetchWorkspaceChatThread(workspaceId, { surface });
  if (!hasWorkspaceChatThread(workspaceThread)) {
    return null;
  }

  threadId = workspaceThread.thread_id;
  if (threadId) {
    deps.setSelectedThreadId(workspaceId, surface, threadId);
  }
  return threadId;
}

function clearEmptySurface(
  deps: LoadWorkspaceThreadDeps,
  workspaceId: string,
  surface: ThreadSurface,
): void {
  if (deps.isViewingSurface(workspaceId, surface)) {
    deps.resetThreadContext();
  }
  if (surface === 'ide' && deps.isCurrentWorkspace(workspaceId)) {
    deps.clearIdeAgentRunLink();
  }
  if (surface === 'operator' && deps.isCurrentWorkspace(workspaceId)) {
    deps.setOperatorThreadEmpty();
  }
}

export async function loadWorkspaceThreadOnce(
  deps: LoadWorkspaceThreadDeps,
  workspaceId: string,
  surface: ThreadSurface,
  requestedThreadId?: string | null,
): Promise<void> {
  let resolvedThreadId = requestedThreadId?.trim() || deps.getSelectedThreadId(workspaceId, surface);
  let attemptedFallback = false;

  try {
    while (true) {
      const threadId = await resolveThreadId(
        deps,
        workspaceId,
        surface,
        attemptedFallback ? null : requestedThreadId,
      );
      if (!threadId) {
        // Selected id may still be set from a wiped thread; clear quietly.
        if (deps.getSelectedThreadId(workspaceId, surface)) {
          deps.clearSelectedThreadId(workspaceId, surface);
        }
        clearEmptySurface(deps, workspaceId, surface);
        return;
      }

      resolvedThreadId = threadId;
      try {
        const history = await fetchThreadHistory(threadId);
        const mapped = deps.filterForSurface(deps.mapChatMessages(history.items), surface);
        deps.applyLoaded(workspaceId, surface, history.thread_id, mapped);
        return;
      } catch (error) {
        // Stale localStorage / open-tab ids 404 after a store wipe — drop them and
        // try the workspace's latest thread once before surfacing an error.
        if (!attemptedFallback && isApiNotFoundError(error)) {
          attemptedFallback = true;
          deps.clearSelectedThreadId(workspaceId, surface);
          continue;
        }
        throw error;
      }
    }
  } catch (error) {
    if (
      !resolvedThreadId ||
      !shouldApplyWorkspaceThreadLoad(
        deps.getSelectedThreadId(workspaceId, surface) ?? resolvedThreadId,
        resolvedThreadId,
      )
    ) {
      return;
    }
    if (isApiTransientError(error)) {
      if (deps.isViewingSurface(workspaceId, surface)) {
        deps.setLoadError(
          error instanceof Error ? error.message : 'Conversation history temporarily unavailable',
        );
      }
      return;
    }
    deps.clearSelectedThreadId(workspaceId, surface);
    if (deps.isViewingSurface(workspaceId, surface)) {
      deps.resetThreadContext();
      // Missing thread after wipe/fallback is an empty dock, not a sticky red error.
      if (!isApiNotFoundError(error)) {
        deps.setLoadError(
          error instanceof Error ? error.message : 'Failed to load conversation history',
        );
      }
    }
    if (surface === 'ide' && deps.isCurrentWorkspace(workspaceId)) {
      deps.clearIdeAgentRunLink();
    }
    if (surface === 'operator' && deps.isCurrentWorkspace(workspaceId)) {
      deps.setOperatorThreadEmpty();
    }
  }
}

export function createWorkspaceThreadLoadQueue() {
  const inflight = new Map<string, Promise<void>>();

  return {
    enqueue(
      workspaceId: string,
      surface: ThreadSurface,
      requestedThreadId: string | null | undefined,
      selectedThreadId: string | null | undefined,
      run: () => Promise<void>,
    ): Promise<void> {
      const key = buildWorkspaceThreadLoadKey(
        workspaceId,
        surface,
        requestedThreadId?.trim() || selectedThreadId,
      );
      const existing = inflight.get(key);
      if (existing) {
        return existing;
      }
      const promise = run().finally(() => {
        inflight.delete(key);
      });
      inflight.set(key, promise);
      return promise;
    },
  };
}
