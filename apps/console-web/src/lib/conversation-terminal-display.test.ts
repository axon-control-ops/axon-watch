import { describe, expect, it } from 'vitest';

import { shouldShowConversationTerminalOutput } from './conversation-terminal-display';

describe('shouldShowConversationTerminalOutput', () => {
  it('shows growing output while open and streaming even when mirrored', () => {
    expect(
      shouldShowConversationTerminalOutput({
        hasOutput: true,
        open: true,
        streaming: true,
        mirrored: true,
        expandedInChat: false,
      }),
    ).toBe(true);
  });

  it('hides closed mirrored output unless expanded in chat', () => {
    expect(
      shouldShowConversationTerminalOutput({
        hasOutput: true,
        open: false,
        streaming: false,
        mirrored: true,
        expandedInChat: false,
      }),
    ).toBe(false);
    expect(
      shouldShowConversationTerminalOutput({
        hasOutput: true,
        open: false,
        streaming: false,
        mirrored: true,
        expandedInChat: true,
      }),
    ).toBe(true);
  });

  it('hides when there is no output', () => {
    expect(
      shouldShowConversationTerminalOutput({
        hasOutput: false,
        open: true,
        streaming: true,
        mirrored: false,
        expandedInChat: false,
      }),
    ).toBe(false);
  });
});
