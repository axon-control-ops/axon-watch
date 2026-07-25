import { describe, expect, it } from 'vitest';

import {
  ideThreadMenuLabel,
  sortIdeThreadsNewestFirst,
  type IdeThreadListItem,
} from './ide-thread-picker-view';

describe('ide thread picker view', () => {
  it('labels threads from preview text', () => {
    const thread: IdeThreadListItem = {
      thread_id: 'thread_a',
      workspace_id: 'workspace_axon_watch',
      run_id: null,
      thread_kind: 'ide',
      created_at: '2026-07-07T12:00:00Z',
      updated_at: '2026-07-07T12:05:00Z',
      preview_label: 'Fix agent dock parity',
    };

    expect(ideThreadMenuLabel(thread)).toBe('Fix agent dock parity');
  });

  it('sorts threads newest first', () => {
    const older: IdeThreadListItem = {
      thread_id: 'thread_old',
      workspace_id: 'workspace_axon_watch',
      run_id: null,
      thread_kind: 'ide',
      created_at: '2026-07-07T10:00:00Z',
      updated_at: '2026-07-07T10:00:00Z',
      preview_label: 'Older',
    };
    const newer: IdeThreadListItem = {
      thread_id: 'thread_new',
      workspace_id: 'workspace_axon_watch',
      run_id: null,
      thread_kind: 'ide',
      created_at: '2026-07-07T12:00:00Z',
      updated_at: '2026-07-07T12:00:00Z',
      preview_label: 'Newer',
    };

    expect(sortIdeThreadsNewestFirst([older, newer]).map((item) => item.thread_id)).toEqual([
      'thread_new',
      'thread_old',
    ]);
  });
});
