import { beforeEach, describe, expect, it } from 'vitest';

import {
  isTransmissionAskAnswered,
  markTransmissionAskAnswered,
  resetTransmissionAskAnswersForTests,
  transmissionAskFingerprint,
} from './vaxon-transmission-reply-state';

describe('vaxon-transmission-reply-state', () => {
  beforeEach(() => {
    resetTransmissionAskAnswersForTests();
  });

  it('hides the CTA immediately after the current ask is answered', () => {
    const line = 'Shall I diagnose it?';
    expect(isTransmissionAskAnswered(line)).toBe(false);
    markTransmissionAskAnswered(line);
    expect(isTransmissionAskAnswered(line)).toBe(true);
  });

  it('does not treat an identical question in a later turn as pre-answered', () => {
    const line = 'Shall I diagnose it?';
    markTransmissionAskAnswered(line);
    expect(isTransmissionAskAnswered(line)).toBe(true);

    // A different question arrives and gets answered in between.
    const nextLine = 'Want me to confirm Watch?';
    expect(isTransmissionAskAnswered(nextLine)).toBe(false);
    markTransmissionAskAnswered(nextLine);
    expect(isTransmissionAskAnswered(nextLine)).toBe(true);

    // The original question's exact text recurs later — must be a fresh ask,
    // not silently suppressed by the earlier answer.
    expect(isTransmissionAskAnswered(line)).toBe(false);
  });

  it('normalizes whitespace/case in fingerprints', () => {
    expect(transmissionAskFingerprint('  Shall I   diagnose it?  ')).toBe(
      transmissionAskFingerprint('shall i diagnose it?'),
    );
  });
});
