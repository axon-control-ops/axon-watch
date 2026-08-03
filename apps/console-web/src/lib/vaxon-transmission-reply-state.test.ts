import { describe, expect, it } from 'vitest';

import {
  isTransmissionAskAnswered,
  markTransmissionAskAnswered,
  pendingTransmissionAsk,
  resetTransmissionAskAnswersForTests,
  retainTransmissionAsk,
} from './vaxon-transmission-reply-state';

describe('VAXON transmission reply state', () => {
  it('keeps an unanswered decision until it is answered', () => {
    const decision = 'Open Attention for the Android CI/CD failure?';
    resetTransmissionAskAnswersForTests();

    retainTransmissionAsk(decision);
    expect(pendingTransmissionAsk.value).toBe(decision);

    markTransmissionAskAnswered(decision);
    expect(isTransmissionAskAnswered(decision)).toBe(true);
    expect(pendingTransmissionAsk.value).toBeNull();
  });
});
