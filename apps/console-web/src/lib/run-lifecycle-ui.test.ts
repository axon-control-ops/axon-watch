import { describe, expect, it } from 'vitest';

import {
  isIdleIncompleteExecutingRun,
  isOperatorCompletablePhase,
  resolveAgentContinuePrompt,
  runContinueActionLabel,
  shouldOfferRunContinue,
} from './run-lifecycle-ui';

describe('run-lifecycle-ui', () => {
  it('allows complete only on review_ready (agent truly done)', () => {
    expect(isOperatorCompletablePhase('review_ready')).toBe(true);
    expect(isOperatorCompletablePhase('executing')).toBe(false);
    expect(isOperatorCompletablePhase('paused')).toBe(false);
  });

  it('blocks complete on terminal phases', () => {
    expect(isOperatorCompletablePhase('completed')).toBe(false);
    expect(isOperatorCompletablePhase('cancelled')).toBe(false);
  });

  it('offers resume only for paused or input-blocked resumable runs', () => {
    expect(
      shouldOfferRunContinue({
        phase: 'executing',
        canResume: false,
        agentStreamActive: false,
        mode: 'agent',
      }),
    ).toBe(false);
    expect(
      shouldOfferRunContinue({
        phase: 'executing',
        canResume: false,
        agentStreamActive: true,
        mode: 'agent',
      }),
    ).toBe(false);
    expect(
      shouldOfferRunContinue({
        phase: 'executing',
        canResume: false,
        agentStreamActive: false,
        mode: 'debug',
      }),
    ).toBe(false);
    expect(
      shouldOfferRunContinue({
        phase: 'executing',
        canResume: false,
        agentStreamActive: false,
        mode: 'ask',
      }),
    ).toBe(false);
    expect(
      shouldOfferRunContinue({
        phase: 'paused',
        canResume: true,
        agentStreamActive: false,
      }),
    ).toBe(true);
    expect(
      shouldOfferRunContinue({
        phase: 'awaiting_input',
        canResume: true,
        agentStreamActive: false,
      }),
    ).toBe(true);
    expect(
      shouldOfferRunContinue({
        phase: 'review_ready',
        canResume: true,
        agentStreamActive: false,
      }),
    ).toBe(false);
  });

  it('labels idle agent execute as CONTINUE', () => {
    expect(
      isIdleIncompleteExecutingRun({
        phase: 'executing',
        agentStreamActive: false,
        mode: 'agent',
      }),
    ).toBe(true);
    expect(
      runContinueActionLabel({
        phase: 'executing',
        agentStreamActive: false,
        mode: 'agent',
      }),
    ).toBe('CONTINUE');
    expect(
      runContinueActionLabel({
        phase: 'paused',
        agentStreamActive: false,
      }),
    ).toBe('RESUME');
  });

  it('resolves continue prompt from linked message then summary', () => {
    expect(
      resolveAgentContinuePrompt({
        runId: 'run_a',
        runSummary: 'fallback summary',
        ideMessages: [
          { role: 'operator', run_id: 'run_a', content: 'fix CI gates' },
          { role: 'agent', run_id: 'run_a', content: 'working' },
        ],
      }),
    ).toBe('fix CI gates');

    expect(
      resolveAgentContinuePrompt({
        runId: 'run_missing',
        runSummary: 'continue',
        ideMessages: [],
        operatorMessages: [],
      }),
    ).toBe('continue');
  });
});
