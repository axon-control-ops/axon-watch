import { describe, expect, it } from 'vitest';

import { applyTerminalInputChunk, sanitizeTerminalInput } from './terminal-input';

describe('terminal-input', () => {
  it('strips xterm bracketed paste markers', () => {
    expect(sanitizeTerminalInput('\x1b[200~curl -s http://example.test\x1b[201~')).toBe(
      'curl -s http://example.test',
    );
  });

  it('clears on clear command submit', () => {
    const result = applyTerminalInputChunk('clear', '\r');
    expect(result.shouldClear).toBe(true);
    expect(result.nextInputLine).toBe('');
  });

  it('clears on reset command submit', () => {
    const result = applyTerminalInputChunk('reset', '\n');
    expect(result.shouldClear).toBe(true);
  });

  it('clears on ctrl+l', () => {
    const result = applyTerminalInputChunk('', '\x0c');
    expect(result.shouldClear).toBe(true);
  });

  it('does not clear unrelated commands', () => {
    const result = applyTerminalInputChunk('ls', '\r');
    expect(result.shouldClear).toBe(false);
  });
});
