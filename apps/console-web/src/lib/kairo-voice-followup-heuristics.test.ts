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

  it('rejects ambient chatter', () => {
    expect(looksLikeOperatorFollowUp('did you see the game last night')).toBe(false);
    expect(looksLikeOperatorFollowUp('nice weather today')).toBe(false);
  });
});
