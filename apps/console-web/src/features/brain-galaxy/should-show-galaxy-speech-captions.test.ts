import { describe, expect, it } from 'vitest';

import { shouldShowGalaxySpeechCaptions } from './should-show-galaxy-speech-captions';

describe('shouldShowGalaxySpeechCaptions', () => {
  it('hides the floating chip on Mission Control so Live Ops owns VAXON', () => {
    expect(
      shouldShowGalaxySpeechCaptions({
        layoutMode: 'operator',
        operatorBrainGalaxyActive: false,
      }),
    ).toBe(false);
  });

  it('keeps captions on Brain Graph', () => {
    expect(
      shouldShowGalaxySpeechCaptions({
        layoutMode: 'operator',
        operatorBrainGalaxyActive: true,
      }),
    ).toBe(true);
  });

  it('stays off in IDE (left rail owns presence)', () => {
    expect(
      shouldShowGalaxySpeechCaptions({
        layoutMode: 'ide',
        operatorBrainGalaxyActive: false,
      }),
    ).toBe(false);
  });
});
