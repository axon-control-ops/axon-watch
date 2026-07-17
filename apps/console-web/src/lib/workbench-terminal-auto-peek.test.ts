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

  it('peeks once per run when the terminal is hidden', () => {
    expect(shouldAutoPeekWorkbenchTerminal(base)).toBe(true);
    expect(
      shouldAutoPeekWorkbenchTerminal({
        ...base,
        layoutMode: 'ide',
      }),
    ).toBe(true);
    expect(
      shouldAutoPeekWorkbenchTerminal({
        ...base,
        alreadyPeekedRunIds: new Set(['run_abc']),
      }),
    ).toBe(false);
  });

  it('also peeks for review_ready output', () => {
    expect(
      shouldAutoPeekWorkbenchTerminal({
        ...base,
        runPhase: 'review_ready',
      }),
    ).toBe(true);
  });

  it('does not peek when the terminal is already open', () => {
    expect(
      shouldAutoPeekWorkbenchTerminal({
        ...base,
        terminalVisible: true,
      }),
    ).toBe(false);
  });

  it('does not peek outside shell layout modes or idle phases', () => {
    expect(
      shouldAutoPeekWorkbenchTerminal({
        ...base,
        layoutMode: 'landing' as unknown as WorkbenchTerminalAutoPeekInput['layoutMode'],
      }),
    ).toBe(false);
    expect(
      shouldAutoPeekWorkbenchTerminal({
        ...base,
        runPhase: 'paused',
      }),
    ).toBe(false);
    expect(
      shouldAutoPeekWorkbenchTerminal({
        ...base,
        runId: null,
      }),
    ).toBe(false);
  });
});
