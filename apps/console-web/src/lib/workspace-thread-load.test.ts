import { describe, expect, it } from 'vitest';

import {
  buildWorkspaceThreadLoadKey,
  isConversationalThreadPreview,
  isEmployeeTitleThreadPreview,
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

  it('classifies roster labels vs conversation previews', () => {
    expect(isEmployeeTitleThreadPreview('Noor · Lead')).toBe(true);
    expect(
      isConversationalThreadPreview(
        'Please check what documents we have in TPS - concerning the NYDA application…',
      ),
    ).toBe(true);
  });

  it('bootstraps active thread from selected, open tabs, then list', () => {
    expect(
      resolveBootstrapIdeThreadId({
        selectedThreadId: 'thread_selected',
        openTabIds: ['thread_tab'],
        threadListIds: ['thread_list'],
        threadPreviewById: {
          thread_selected: 'Continue the migration plan',
          thread_tab: 'Tab history',
          thread_list: 'List history',
        },
      }),
    ).toBe('thread_selected');
    expect(
      resolveBootstrapIdeThreadId({
        selectedThreadId: null,
        openTabIds: ['thread_tab'],
        threadListIds: ['thread_list'],
        threadPreviewById: {
          thread_tab: 'Tab history',
          thread_list: 'List history',
        },
      }),
    ).toBe('thread_tab');
    expect(
      resolveBootstrapIdeThreadId({
        selectedThreadId: null,
        openTabIds: [],
        threadListIds: ['thread_list'],
        threadPreviewById: {
          thread_list: 'List history',
        },
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

  it('prefers the newest conversational thread over an empty teammate tab', () => {
    expect(
      resolveBootstrapIdeThreadId({
        selectedThreadId: 'thread_noor',
        openTabIds: ['thread_noor', 'thread_work'],
        threads: [
          {
            thread_id: 'thread_noor',
            preview_label: 'Noor · Lead',
            updated_at: '2026-07-22T15:59:36Z',
          },
          {
            thread_id: 'thread_work',
            preview_label: 'Please check what documents we have in TPS - concerning the NYDA applic…',
            updated_at: '2026-08-19T11:48:10Z',
          },
        ],
      }),
    ).toBe('thread_work');
  });
});
