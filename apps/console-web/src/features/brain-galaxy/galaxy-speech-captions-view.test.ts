import { describe, expect, it } from 'vitest';

import {
  buildNarrationSentenceSteps,
  splitGalaxySpeechPhrases,
} from './galaxy-speech-captions-view';

describe('galaxy-speech-captions-view', () => {
  it('splits speech into one line per sentence', () => {
    const phrases = splitGalaxySpeechPhrases(
      'Systems are nominal across DashPro. I am watching the active Prettier wave and will call out blockers.',
    );
    expect(phrases).toEqual([
      'Systems are nominal across DashPro.',
      'I am watching the active Prettier wave and will call out blockers.',
    ]);
  });

  it('keeps a single sentence intact even when long', () => {
    const long =
      'Lead for priorities Night Watch for signals health specialists for their owns and that is the daily loop.';
    expect(splitGalaxySpeechPhrases(long)).toEqual([long]);
  });

  it('builds narration steps that start immediately then advance by word share', () => {
    const steps = buildNarrationSentenceSteps(
      'Alpha stays on stage alone. Beta follows after the first sentence.',
    );
    expect(steps).toHaveLength(2);
    expect(steps[0]).toMatchObject({ phrase: 'Alpha stays on stage alone.', delayMs: 0 });
    expect(steps[1]?.phrase).toBe('Beta follows after the first sentence.');
    expect(steps[1]?.delayMs ?? 0).toBeGreaterThan(0);
  });

  it('returns a single zero-delay step for one-sentence chunks', () => {
    expect(buildNarrationSentenceSteps('Listening.')).toEqual([
      { phrase: 'Listening.', delayMs: 0 },
    ]);
  });
});
