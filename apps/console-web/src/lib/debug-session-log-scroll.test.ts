import { describe, expect, it } from 'vitest';

import {
  isDebugLogPinnedToBottom,
  scrollDebugLogToBottom,
} from './debug-session-log-scroll';

describe('debug-session-log-scroll', () => {
  it('treats near-bottom as pinned', () => {
    expect(
      isDebugLogPinnedToBottom({ scrollTop: 200, clientHeight: 100, scrollHeight: 330 }),
    ).toBe(true);
    expect(
      isDebugLogPinnedToBottom({ scrollTop: 0, clientHeight: 100, scrollHeight: 400 }),
    ).toBe(false);
  });

  it('scrolls to the bottom of the feed', () => {
    const el = { scrollTop: 0, scrollHeight: 480 };
    expect(scrollDebugLogToBottom(el)).toBe(480);
    expect(el.scrollTop).toBe(480);
  });
});
