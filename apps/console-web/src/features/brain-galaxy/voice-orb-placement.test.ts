import { describe, expect, it } from 'vitest';

import {
  normalizeVoiceOrbDock,
  parsePersistedVoiceOrbPlacement,
  resolvePlacementForDock,
} from './voice-orb-placement';

describe('voice-orb-placement', () => {
  it('normalizes dock aliases', () => {
    expect(normalizeVoiceOrbDock('bottom_left')).toBe('bottom-left');
    expect(normalizeVoiceOrbDock('TOP-RIGHT')).toBe('top-right');
    expect(normalizeVoiceOrbDock('nope')).toBeNull();
  });

  it('parses persisted viewport placement', () => {
    expect(
      parsePersistedVoiceOrbPlacement(
        JSON.stringify({ dock: 'bottom-left', x: 20, y: 40, userPinned: true }),
      ),
    ).toEqual({
      dock: 'bottom-left',
      x: 20,
      y: 40,
      userPinned: true,
      visible: true,
    });
  });

  it('resolves dock placement inside the viewport', () => {
    expect(
      resolvePlacementForDock({
        dock: 'center',
        viewport: { width: 1000, height: 800 },
        orb: { width: 200, height: 200 },
      }),
    ).toEqual({ x: 400, y: 300 });
  });
});
