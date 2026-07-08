import { describe, expect, it } from 'vitest';

import { shouldPrimeRuntimeAssistantCue } from './runtime-assistant-heuristics';

describe('runtime assistant heuristics', () => {
  it('primes the cue for open-ended assistant questions', () => {
    expect(shouldPrimeRuntimeAssistantCue('why is DashPro spiking?')).toBe(true);
    expect(shouldPrimeRuntimeAssistantCue('walk me through what happened')).toBe(true);
  });

  it('does not prime the cue for fast operator status or command turns', () => {
    expect(shouldPrimeRuntimeAssistantCue('any approvals?')).toBe(false);
    expect(shouldPrimeRuntimeAssistantCue('git status')).toBe(false);
    expect(shouldPrimeRuntimeAssistantCue('open attention')).toBe(false);
  });
});
