import { describe, expect, it } from 'vitest';

import {
  elementCanScrollInDirection,
  isConversationNearBottom,
  overflowYAllowsScroll,
  pinConversationScrollToBottom,
} from './conversation-seam-scroll';

describe('conversation-seam-scroll', () => {
  it('only treats auto/scroll overflow as user-scrollable', () => {
    expect(overflowYAllowsScroll('auto')).toBe(true);
    expect(overflowYAllowsScroll('scroll')).toBe(true);
    expect(overflowYAllowsScroll('hidden')).toBe(false);
    expect(overflowYAllowsScroll('visible')).toBe(false);
  });

  it('ignores clipped overflow:hidden blocks when routing wheel events', () => {
    expect(
      elementCanScrollInDirection(
        {
          scrollTop: 0,
          clientHeight: 100,
          scrollHeight: 400,
          overflowY: 'hidden',
        },
        40,
      ),
    ).toBe(false);
  });

  it('allows nested auto overflow only while room remains', () => {
    expect(
      elementCanScrollInDirection(
        {
          scrollTop: 0,
          clientHeight: 100,
          scrollHeight: 400,
          overflowY: 'auto',
        },
        40,
      ),
    ).toBe(true);
    expect(
      elementCanScrollInDirection(
        {
          scrollTop: 300,
          clientHeight: 100,
          scrollHeight: 400,
          overflowY: 'auto',
        },
        40,
      ),
    ).toBe(false);
  });

  it('pins near-bottom detection and scroll helper', () => {
    const el = { scrollTop: 0, clientHeight: 200, scrollHeight: 500 };
    expect(isConversationNearBottom(el, 72)).toBe(false);
    pinConversationScrollToBottom(el);
    expect(el.scrollTop).toBe(500);
    el.scrollTop = 500 - 200 - 40;
    expect(isConversationNearBottom(el, 72)).toBe(true);
  });
});
