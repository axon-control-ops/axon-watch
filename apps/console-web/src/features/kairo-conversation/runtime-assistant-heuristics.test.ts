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

  it('primes the cue for Chief of Staff / long executive prompts', () => {
    expect(shouldPrimeRuntimeAssistantCue('You are VAXON. Chief of Staff charter follows.')).toBe(
      true,
    );
    expect(shouldPrimeRuntimeAssistantCue(`${'plan the mission. '.repeat(40)}`)).toBe(true);
  });
});

