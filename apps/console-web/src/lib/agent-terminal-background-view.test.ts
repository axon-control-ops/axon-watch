import { describe, expect, it } from 'vitest';

import { shouldShowAgentTerminalBackgroundControl } from './agent-terminal-background-view';

describe('agent terminal background visibility', () => {
  it('hides when the agent run is not stoppable', () => {
    expect(
      shouldShowAgentTerminalBackgroundControl({
        canStopIdeAgentRun: false,
        terminalBlockRunning: true,
        agentTerminalFocused: true,
      }),
    ).toBe(false);
  });

  it('shows on a running terminal transcript block', () => {
    expect(
      shouldShowAgentTerminalBackgroundControl({
        canStopIdeAgentRun: true,
        terminalBlockRunning: true,
      }),
    ).toBe(true);
  });

  it('shows when the agent terminal dock is focused during a stoppable run', () => {
    expect(
      shouldShowAgentTerminalBackgroundControl({
        canStopIdeAgentRun: true,
        agentTerminalFocused: true,
      }),
    ).toBe(true);
  });

  it('hides when neither a running block nor agent terminal focus applies', () => {
    expect(
      shouldShowAgentTerminalBackgroundControl({
        canStopIdeAgentRun: true,
      }),
    ).toBe(false);
  });
});
