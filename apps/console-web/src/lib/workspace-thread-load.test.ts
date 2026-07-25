import { describe, expect, it } from 'vitest';

import {
  buildWorkspaceThreadLoadKey,
  resolveBootstrapIdeThreadId,
  shouldApplyWorkspaceThreadLoad,
} from './workspace-thread-load';

describe('workspace-thread-load', () => {
  it('keys inflight loads by workspace, surface, and thread target', () => {
    expect(buildWorkspaceThreadLoadKey('ws_1', 'ide')).toBe('ws_1:ide:auto');
    expect(buildWorkspaceThreadLoadKey('ws_1', 'ide', 'thread_a')).toBe('ws_1:ide:thread_a');
  });

  it('drops stale history when the selected tab changed', () => {
    expect(shouldApplyWorkspaceThreadLoad('thread_b', 'thread_a')).toBe(false);
    expect(shouldApplyWorkspaceThreadLoad('thread_a', 'thread_a')).toBe(true);
    expect(shouldApplyWorkspaceThreadLoad(null, 'thread_a')).toBe(true);
  });

  it('bootstraps active thread from selected, open tabs, then list', () => {
    expect(
      resolveBootstrapIdeThreadId({
        selectedThreadId: 'thread_selected',
        openTabIds: ['thread_tab'],
        threadListIds: ['thread_list'],
      }),
    ).toBe('thread_selected');
    expect(
      resolveBootstrapIdeThreadId({
        selectedThreadId: null,
        openTabIds: ['thread_tab'],
        threadListIds: ['thread_list'],
      }),
    ).toBe('thread_tab');
    expect(
      resolveBootstrapIdeThreadId({
        selectedThreadId: null,
        openTabIds: [],
        threadListIds: ['thread_list'],
      }),
    ).toBe('thread_list');
  });

  it('skips empty New chat selection when titled history exists', () => {
    expect(
      resolveBootstrapIdeThreadId({
        selectedThreadId: 'thread_empty',
        openTabIds: ['thread_empty', 'thread_history'],
        threadListIds: ['thread_empty', 'thread_history'],
        threadPreviewById: {
          thread_empty: 'New chat',
          thread_history: 'Quinn · Integrations',
        },
      }),
    ).toBe('thread_history');
  });
});
