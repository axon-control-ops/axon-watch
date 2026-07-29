import { describe, expect, it } from 'vitest';

import {
  CURSOR_SHELL_PROCESS_DETACH_AVAILABLE,
  agentTerminalMirrorBadgeLabel,
  agentTranscriptHasOpenTerminalBlock,
  shouldShowAgentTerminalBackgroundControl,
} from './agent-terminal-background-view';

describe('agent terminal background visibility', () => {
  it('hides when the agent run is not stoppable', () => {
    expect(
      shouldShowAgentTerminalBackgroundControl({
        canStopIdeAgentRun: false,
        terminalBlockRunning: true,
      }),
    ).toBe(false);
  });

  it('shows only while an in-thread shell block is still open', () => {
    expect(
      shouldShowAgentTerminalBackgroundControl({
        canStopIdeAgentRun: true,
        terminalBlockRunning: true,
      }),
    ).toBe(true);
  });

  it('hides once the shell tool has finished (Cursor: no re-run on history cards)', () => {
    expect(
      shouldShowAgentTerminalBackgroundControl({
        canStopIdeAgentRun: true,
        terminalBlockRunning: false,
      }),
    ).toBe(false);
  });

  it('hides for a busy agent with no open shell block', () => {
    expect(
      shouldShowAgentTerminalBackgroundControl({
        canStopIdeAgentRun: true,
        terminalBlockRunning: false,
      }),
    ).toBe(false);
  });

  it('detects open vs closed terminal blocks in transcript content', () => {
    expect(agentTranscriptHasOpenTerminalBlock(':::terminal npm test\nrunning…')).toBe(true);
    expect(
      agentTranscriptHasOpenTerminalBlock([':::terminal npm test', 'ok', ':::'].join('\n')),
    ).toBe(false);
    expect(agentTranscriptHasOpenTerminalBlock(':::thinking\nstill going')).toBe(false);
  });

  it('labels watching shells honestly while process detach is unavailable', () => {
    expect(CURSOR_SHELL_PROCESS_DETACH_AVAILABLE).toBe(false);
    expect(
      agentTerminalMirrorBadgeLabel({
        segmentOpen: true,
        mirrorActive: true,
      }),
    ).toBe('watching in terminal');
    expect(
      agentTerminalMirrorBadgeLabel({
        segmentOpen: false,
        mirrorActive: true,
      }),
    ).toBe('shown in terminal');
    expect(
      agentTerminalMirrorBadgeLabel({
        segmentOpen: true,
        mirrorActive: false,
      }),
    ).toBeNull();
  });
});
