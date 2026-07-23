import { describe, expect, it } from 'vitest';

import {
  shouldAutoPeekWorkbenchTerminal,
  type WorkbenchTerminalAutoPeekInput,
} from './workbench-terminal-auto-peek';

describe('shouldAutoPeekWorkbenchTerminal', () => {
  const base = {
    layoutMode: 'operator' as const,
    terminalVisible: false,
    runPhase: 'executing',
    runId: 'run_abc',
    alreadyPeekedRunIds: new Set<string>(),
  };

  it('never auto-opens the terminal (operator must reveal it)', () => {
    expect(shouldAutoPeekWorkbenchTerminal(base)).toBe(false);
    expect(
      shouldAutoPeekWorkbenchTerminal({
        ...base,
        layoutMode: 'ide',
        runPhase: 'review_ready',
      }),
    ).toBe(false);
    expect(
      shouldAutoPeekWorkbenchTerminal({
        ...base,
        terminalVisible: true,
      }),
    ).toBe(false);
    expect(
      shouldAutoPeekWorkbenchTerminal({
        ...base,
        layoutMode: 'landing' as unknown as WorkbenchTerminalAutoPeekInput['layoutMode'],
        runId: null,
        runPhase: 'paused',
      }),
    ).toBe(false);
  });
});
