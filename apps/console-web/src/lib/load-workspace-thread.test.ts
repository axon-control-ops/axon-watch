import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../api/control-plane', () => ({
  fetchThreadHistory: vi.fn(),
  fetchWorkspaceChatThread: vi.fn(),
  hasWorkspaceChatThread: vi.fn(),
}));

import {
  fetchThreadHistory,
  fetchWorkspaceChatThread,
  hasWorkspaceChatThread,
} from '../api/control-plane';
import { ApiRequestError } from '../api/client';
import { loadWorkspaceThreadOnce, type LoadWorkspaceThreadDeps } from './load-workspace-thread';

describe('loadWorkspaceThreadOnce', () => {
  const fetchHistory = vi.mocked(fetchThreadHistory);
  const fetchWorkspaceThread = vi.mocked(fetchWorkspaceChatThread);
  const hasThread = vi.mocked(hasWorkspaceChatThread);

  let selected: string | null;
  let deps: LoadWorkspaceThreadDeps;

  beforeEach(() => {
    selected = 'thread_stale';
    deps = {
      getSelectedThreadId: () => selected,
      setSelectedThreadId: (_ws, _surface, threadId) => {
        selected = threadId;
      },
      clearSelectedThreadId: () => {
        selected = null;
      },
      isViewingSurface: () => true,
      isCurrentWorkspace: () => true,
      applyLoaded: vi.fn(),
      resetThreadContext: vi.fn(),
      clearIdeAgentRunLink: vi.fn(),
      setOperatorThreadEmpty: vi.fn(),
      setLoadError: vi.fn(),
      mapChatMessages: (items) =>
        items.map((item) => ({
          message_id: item.message_id,
          thread_id: item.thread_id,
          role: item.role,
          content: item.content,
          created_at: item.created_at,
        })),
      filterForSurface: (messages) => messages,
    };
    vi.clearAllMocks();
  });

  it('clears a missing selected thread and loads the workspace latest without sticky error', async () => {
    fetchHistory
      .mockRejectedValueOnce(new ApiRequestError('thread history fetch failed', 404))
      .mockResolvedValueOnce({
        thread_id: 'thread_latest',
        workspace_id: 'ws_1',
        run_id: null,
        items: [
          {
            message_id: 'message_1',
            thread_id: 'thread_latest',
            workspace_id: 'ws_1',
            run_id: null,
            role: 'operator',
            content: 'hello',
            created_at: '2026-07-13T00:00:00Z',
          },
        ],
        count: 1,
      });
    fetchWorkspaceThread.mockResolvedValue({
      thread_id: 'thread_latest',
      workspace_id: 'ws_1',
      run_id: null,
      updated_at: '2026-07-13T00:00:00Z',
    });
    hasThread.mockReturnValue(true);

    await loadWorkspaceThreadOnce(deps, 'ws_1', 'ide', 'thread_stale');

    expect(deps.setLoadError).not.toHaveBeenCalled();
    expect(deps.applyLoaded).toHaveBeenCalledWith(
      'ws_1',
      'ide',
      'thread_latest',
      expect.any(Array),
    );
    expect(selected).toBe('thread_latest');
  });

  it('clears wiped state quietly when no workspace thread remains', async () => {
    fetchHistory.mockRejectedValue(new ApiRequestError('thread history fetch failed', 404));
    fetchWorkspaceThread.mockResolvedValue({
      thread_id: null,
      workspace_id: 'ws_1',
      run_id: null,
      updated_at: null,
    });
    hasThread.mockReturnValue(false);

    await loadWorkspaceThreadOnce(deps, 'ws_1', 'ide', 'thread_stale');

    expect(deps.setLoadError).not.toHaveBeenCalled();
    expect(deps.resetThreadContext).toHaveBeenCalled();
    expect(selected).toBeNull();
  });
});
