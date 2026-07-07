import { describe, expect, it } from 'vitest';

import {
  isIdeInterruptStopDisabled,
  resolveIdeInterruptStopTarget,
  shouldShowIdeInterruptStop,
} from './ide-interrupt-panel-view';

describe('ide interrupt panel view', () => {
  it('prefers IDE agent stop when the composer stream is active', () => {
    expect(
      shouldShowIdeInterruptStop({
        canStopIdeAgentRun: true,
        canStopPrimaryRun: false,
        primaryRunPhase: 'executing',
        agentStreamActive: true,
      }),
    ).toBe(true);

    expect(
      resolveIdeInterruptStopTarget({
        canStopIdeAgentRun: true,
        agentStreamActive: true,
      }),
    ).toBe('ide-agent');
  });

  it('falls back to primary run stop when no IDE agent run is active', () => {
    expect(
      resolveIdeInterruptStopTarget({
        canStopIdeAgentRun: false,
        agentStreamActive: false,
      }),
    ).toBe('primary');
  });

  it('disables stop while mutation is in flight unless IDE agent stop is available', () => {
    expect(
      isIdeInterruptStopDisabled({
        runMutationStopping: true,
        canStopIdeAgentRun: false,
        canStopPrimaryRun: true,
        primaryRunPhase: 'executing',
      }),
    ).toBe(true);

    expect(
      isIdeInterruptStopDisabled({
        runMutationStopping: true,
        canStopIdeAgentRun: true,
        canStopPrimaryRun: false,
        primaryRunPhase: 'executing',
      }),
    ).toBe(true);
  });
});
