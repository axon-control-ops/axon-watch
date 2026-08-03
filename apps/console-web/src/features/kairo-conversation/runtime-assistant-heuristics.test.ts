import { describe, expect, it } from 'vitest';

import { shouldPrimeRuntimeAssistantCue } from './runtime-assistant-heuristics';

describe('runtime assistant heuristics', () => {
  it('primes the cue for open-ended questions that are not live-ops status', () => {
    expect(shouldPrimeRuntimeAssistantCue('walk me through what happened')).toBe(true);
    expect(shouldPrimeRuntimeAssistantCue('what do you think we should prioritize next week?')).toBe(
      true,
    );
  });

  it('does not prime the cue for fleet, critical, or command turns', () => {
    expect(
      shouldPrimeRuntimeAssistantCue('Why are we having 50 CRITICAL ISSUES in DashPro'),
    ).toBe(false);
    expect(shouldPrimeRuntimeAssistantCue('why is DashPro spiking?')).toBe(false);
    expect(shouldPrimeRuntimeAssistantCue('any approvals?')).toBe(false);
    expect(shouldPrimeRuntimeAssistantCue('git status')).toBe(false);
    expect(shouldPrimeRuntimeAssistantCue('open attention')).toBe(false);
  });
});
