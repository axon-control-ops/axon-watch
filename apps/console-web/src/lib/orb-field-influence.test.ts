import { describe, expect, it } from 'vitest';

import {
  orbCenter,
  orbVisualRadius,
  sampleOrbFieldInfluence,
} from './orb-field-influence';

describe('orb-field-influence', () => {
  const orb = { x: 100, y: 100, width: 200, height: 260 };

  it('computes visual radius inside the orb frame', () => {
    expect(orbVisualRadius(orb)).toBeCloseTo(90, 5);
    expect(orbCenter(orb)).toEqual({ x: 200, y: 230 });
  });

  it('returns null when the card is far from the orb', () => {
    expect(
      sampleOrbFieldInfluence({
        orb,
        element: { left: 800, top: 600, width: 160, height: 90 },
      }),
    ).toBeNull();
  });

  it('pushes overlapping cards away and enables a circular bite mask', () => {
    const sample = sampleOrbFieldInfluence({
      orb,
      element: { left: 180, top: 200, width: 160, height: 90 },
    });
    expect(sample).not.toBeNull();
    expect(sample!.influence).toBeGreaterThan(0.2);
    expect(Math.abs(sample!.pushX) + Math.abs(sample!.pushY)).toBeGreaterThan(2);
    expect(sample!.mask).toBe(true);
    expect(sample!.biteR).toBeGreaterThan(orbVisualRadius(orb));
  });

  it('exposes bite geometry for CSS mask application', () => {
    const sample = sampleOrbFieldInfluence({
      orb,
      element: { left: 180, top: 200, width: 160, height: 90 },
    });
    expect(sample).not.toBeNull();
    expect(sample!.localX).toBeGreaterThan(0);
    expect(sample!.localY).toBeGreaterThan(0);
    expect(sample!.radius).toContain('rem');
  });
});
