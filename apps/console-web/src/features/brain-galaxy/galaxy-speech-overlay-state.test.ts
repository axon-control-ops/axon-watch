import { describe, expect, it } from 'vitest';

import {
  galaxySpeechOverlayActive,
  setGalaxySpeechOverlayActive,
} from './galaxy-speech-overlay-state';

describe('galaxy-speech-overlay-state', () => {
  it('toggles overlay active for speech-driven stage chrome', () => {
    setGalaxySpeechOverlayActive(false);
    expect(galaxySpeechOverlayActive.value).toBe(false);
    setGalaxySpeechOverlayActive(true);
    expect(galaxySpeechOverlayActive.value).toBe(true);
    setGalaxySpeechOverlayActive(false);
    expect(galaxySpeechOverlayActive.value).toBe(false);
  });
});
