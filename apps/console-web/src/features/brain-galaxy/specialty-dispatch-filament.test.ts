import { describe, expect, it } from 'vitest';
import { Vector3 } from 'three';

import {
  SPECIALTY_DISPATCH_DURATION_MS,
  animateSpecialtyDispatchFilament,
  buildSpecialtyDispatchFilament,
  disposeSpecialtyDispatchFilament,
  formatSpecialtyRouteChip,
} from './specialty-dispatch-filament';

describe('formatSpecialtyRouteChip', () => {
  it('formats target role and optional from', () => {
    expect(
      formatSpecialtyRouteChip({
        toName: 'Priya',
        toRoleLabel: 'Frontend',
        fromName: 'Marco',
      }),
    ).toBe('→ Priya · Frontend · from Marco');
  });

  it('omits blank from', () => {
    expect(
      formatSpecialtyRouteChip({
        toName: 'Priya',
        toRoleLabel: 'Frontend',
      }),
    ).toBe('→ Priya · Frontend');
  });
});

describe('specialty dispatch filament', () => {
  it('animates then expires', () => {
    const fx = buildSpecialtyDispatchFilament({
      from: new Vector3(0, 0, 0),
      to: new Vector3(1.3, 0.2, 0.4),
      label: '→ Priya · Frontend',
      nowMs: 1_000,
    });
    expect(animateSpecialtyDispatchFilament(fx, 1_000)).toBe(true);
    expect(
      animateSpecialtyDispatchFilament(fx, 1_000 + SPECIALTY_DISPATCH_DURATION_MS + 1),
    ).toBe(false);
    disposeSpecialtyDispatchFilament(fx);
  });
});
