import { describe, expect, it } from 'vitest';

import { looksLikeOperatorFollowUp } from './kairo-voice-followup-heuristics';

describe('kairo voice follow-up heuristics', () => {
  it('accepts short clarifications and follow-up cues', () => {
    expect(looksLikeOperatorFollowUp('and DashPro')).toBe(true);
    expect(looksLikeOperatorFollowUp('what about DashPro')).toBe(true);
    expect(looksLikeOperatorFollowUp('anything else on fleet health')).toBe(true);
  });

  it('accepts question-shaped follow-ups', () => {
    expect(looksLikeOperatorFollowUp('how is dashpro doing')).toBe(true);
    expect(looksLikeOperatorFollowUp('still degraded?')).toBe(true);
  });

  it('accepts natural requests that start with filler (okay/can you…)', () => {
    expect(
      looksLikeOperatorFollowUp(
        'okay can you turn a little bit about the best paid critical issues',
      ),
    ).toBe(true);
    expect(looksLikeOperatorFollowUp('alright please check DashPro')).toBe(true);
  });
});
