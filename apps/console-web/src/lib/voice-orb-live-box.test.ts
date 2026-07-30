import { describe, expect, it } from 'vitest';

import {
  measureVoiceOrbLiveBox,
  voiceOrbBoxFromPosition,
  VOICE_ORB_CORE_SELECTOR,
  VOICE_ORB_FALLBACK_SIZE,
  VOICE_ORB_ROOT_SELECTOR,
} from './voice-orb-live-box';

function fakeEl(box: { left: number; top: number; width: number; height: number }): Element {
  return {
    getBoundingClientRect: () => ({
      left: box.left,
      top: box.top,
      width: box.width,
      height: box.height,
      right: box.left + box.width,
      bottom: box.top + box.height,
      x: box.left,
      y: box.top,
      toJSON: () => ({}),
    }),
  } as unknown as Element;
}

describe('voice-orb-live-box', () => {
  it('square-packs the circular core rect for the floating viewport orb', () => {
    const box = measureVoiceOrbLiveBox((selector) =>
      selector === VOICE_ORB_CORE_SELECTOR
        ? fakeEl({ left: 40, top: 60, width: 180, height: 220 })
        : null,
    );
    expect(box).toEqual({ x: 40, y: 80, width: 180, height: 180 });
  });

  it('ignores embedded Mission Control orbs (viewport selector only)', () => {
    expect(VOICE_ORB_CORE_SELECTOR).toContain('jarvis-float--viewport');
    expect(VOICE_ORB_ROOT_SELECTOR).toContain('jarvis-float--viewport');
    expect(measureVoiceOrbLiveBox(() => null)).toBeNull();
  });

  it('falls back to store position', () => {
    expect(voiceOrbBoxFromPosition({ x: 10, y: 20 })).toEqual({
      x: 10,
      y: 20,
      width: VOICE_ORB_FALLBACK_SIZE.width,
      height: VOICE_ORB_FALLBACK_SIZE.height,
    });
  });
});
