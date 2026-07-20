import { describe, expect, it } from 'vitest';

import {
  closeIdeThreadTab,
  ensureOpenIdeThreadTabs,
  openIdeThreadTab,
  pruneOpenIdeThreadTabs,
  resolveIdeThreadTabAfterClose,
  resolveOpenIdeThreadTabItems,
  seedOpenIdeTabsFromHistory,
} from './ide-thread-tabs-view';

describe('ide thread tabs view', () => {
  it('opens tabs without duplicates', () => {
    expect(openIdeThreadTab(['a'], 'b')).toEqual(['a', 'b']);
    expect(openIdeThreadTab(['a'], 'a')).toEqual(['a']);
  });

  it('selects a neighbor when closing the active tab', () => {
    expect(
      resolveIdeThreadTabAfterClose({
        openIds: ['a', 'b', 'c'],
        closedId: 'b',
        activeId: 'b',
      }),
    ).toBe('c');
  });

  it('keeps the active tab when closing a different tab', () => {
    expect(
      resolveIdeThreadTabAfterClose({
        openIds: ['a', 'b', 'c'],
        closedId: 'a',
        activeId: 'b',
      }),
    ).toBe('b');
  });

  it('prunes stale tabs and seeds from fallback', () => {
    expect(pruneOpenIdeThreadTabs(['a', 'b'], ['b', 'c'])).toEqual(['b']);
    expect(ensureOpenIdeThreadTabs([], 'thread_1')).toEqual(['thread_1']);
    expect(closeIdeThreadTab(['a', 'b'], 'a')).toEqual(['b']);
  });

  it('keeps active thread visible before catalog metadata loads', () => {
    expect(
      resolveOpenIdeThreadTabItems({
        openIds: [],
        threads: [],
        activeThreadId: 'thread_live',
        workspaceId: 'workspace_dashpro',
      }).map((thread) => thread.thread_id),
    ).toEqual(['thread_live']);
  });

  it('reseeds open tabs from titled history when only New chat slots remain', () => {
    expect(
      seedOpenIdeTabsFromHistory({
        openIds: ['thread_new_a', 'thread_new_b'],
        activeThreadId: 'thread_new_a',
        threads: [
          {
            thread_id: 'thread_new_a',
            preview_label: 'New chat',
            updated_at: '2026-07-18T10:00:00Z',
          },
          {
            thread_id: 'thread_new_b',
            preview_label: 'New chat',
            updated_at: '2026-07-18T10:01:00Z',
          },
          {
            thread_id: 'thread_quinn',
            preview_label: 'Quinn · Integrations',
            updated_at: '2026-07-18T09:00:00Z',
          },
          {
            thread_id: 'thread_worker',
            preview_label: 'Look at the Worker/Employee Agents',
            updated_at: '2026-07-18T08:00:00Z',
          },
        ],
      }),
    ).toEqual(['thread_new_a', 'thread_quinn', 'thread_worker']);
  });
});
