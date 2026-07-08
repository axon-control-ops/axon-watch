import { describe, expect, it } from 'vitest';

import { resolveOrbPointerUpIntent } from './kairo-galaxy-orb-interaction';

describe('resolveOrbPointerUpIntent', () => {
  it('allows a hands-free tap to toggle back to manual', () => {
    expect(
      resolveOrbPointerUpIntent({
        captureActive: true,
        handsFreeEnabled: true,
        heldMs: 80,
        holdToTalkMs: 280,
      }),
    ).toEqual({
      stopCapture: false,
      suppressToggleClick: false,
    });
  });

  it('keeps manual hold-to-talk release from toggling modes', () => {
    expect(
      resolveOrbPointerUpIntent({
        captureActive: true,
        handsFreeEnabled: false,
        heldMs: 420,
        holdToTalkMs: 280,
      }),
    ).toEqual({
      stopCapture: true,
      suppressToggleClick: true,
    });
  });

  it('suppresses click after a long press even if capture never started', () => {
    expect(
      resolveOrbPointerUpIntent({
        captureActive: false,
        handsFreeEnabled: false,
        heldMs: 320,
        holdToTalkMs: 280,
      }),
    ).toEqual({
      stopCapture: false,
      suppressToggleClick: true,
    });
  });
});
