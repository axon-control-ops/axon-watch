import { describe, expect, it } from 'vitest';

import {
  opportunisticCandidateToSpokenAlert,
  selectOpportunisticSpeech,
} from './opportunistic-speech-policy';

describe('opportunistic speech policy', () => {
  it('only speaks while console is active and under interruption budget', () => {
    const candidates = [
      { kind: 'reminder' as const, text: 'Reminder: stretch', memoryId: 'm1' },
    ];
    expect(
      selectOpportunisticSpeech({
        consoleActive: false,
        quietHours: false,
        interruptionsUsed: 0,
        maxInterruptionsPerHour: 4,
        candidates,
      }),
    ).toBeNull();
    const chosen = selectOpportunisticSpeech({
      consoleActive: true,
      quietHours: false,
      interruptionsUsed: 0,
      maxInterruptionsPerHour: 4,
      candidates,
    });
    expect(chosen?.kind).toBe('reminder');
    const alert = opportunisticCandidateToSpokenAlert(chosen!);
    expect(alert.eligible).toBe(true);
    expect(alert.reason).toContain('reminder');
  });
});
