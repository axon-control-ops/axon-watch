import { describe, expect, it } from 'vitest';

import { conversationMessageWindow } from './conversation-message-window';

describe('conversation message window', () => {
  const messages = Array.from({ length: 233 }, (_, index) => `message-${index}`);

  it('renders only the latest page by default', () => {
    const window = conversationMessageWindow(messages, 0, 40);
    expect(window.items).toHaveLength(40);
    expect(window.items[0]).toBe('message-193');
    expect(window.items.at(-1)).toBe('message-232');
    expect(window.olderCount).toBe(193);
    expect(window.newerCount).toBe(0);
  });

  it('pages backward without increasing mounted message count', () => {
    const window = conversationMessageWindow(messages, 1, 40);
    expect(window.items).toHaveLength(40);
    expect(window.items[0]).toBe('message-153');
    expect(window.items.at(-1)).toBe('message-192');
    expect(window.olderCount).toBe(153);
    expect(window.newerCount).toBe(40);
  });

  it('clamps the oldest partial page', () => {
    const window = conversationMessageWindow(messages, 99, 40);
    expect(window.page).toBe(5);
    expect(window.items).toEqual(messages.slice(0, 33));
    expect(window.olderCount).toBe(0);
    expect(window.newerCount).toBe(200);
  });
});
