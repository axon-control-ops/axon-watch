import { describe, expect, it } from 'vitest';

import {
  ORB_FIELD_DRAG_MAX_PUSH,
  ORB_FIELD_MAX_PUSH,
  orbVisualRadius,
  sampleOrbFieldInfluence,
} from './orb-field-influence';

describe('orb-field-influence', () => {
  const orb = { x: 100, y: 100, width: 200, height: 200 };

  it('returns null when far away', () => {
    expect(
      sampleOrbFieldInfluence({
        orb,
        element: { left: 900, top: 700, width: 160, height: 90 },
      }),
    ).toBeNull();
  });

  it('produces a strong bite + push when overlapping', () => {
    const sample = sampleOrbFieldInfluence({
      orb,
      element: { left: 170, top: 160, width: 160, height: 90 },
    });
    expect(sample).not.toBeNull();
    expect(sample!.mask).toBe(true);
    expect(sample!.biteR).toBeGreaterThan(orbVisualRadius(orb));
    expect(Math.abs(sample!.pushX) + Math.abs(sample!.pushY)).toBeGreaterThan(16);
  });

  it('uses a larger drag budget than idle', () => {
    expect(ORB_FIELD_DRAG_MAX_PUSH).toBeGreaterThan(ORB_FIELD_MAX_PUSH);
  });
});
