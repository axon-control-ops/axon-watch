import { describe, expect, it } from 'vitest';

import { motionIntensityFromStorage, planMotionTransition } from './motion-orchestrator';

describe('planMotionTransition', () => {
  it('scales duration by intensity', () => {
    const subtle = planMotionTransition('panel_open', { intensity: 'subtle' });
    const cinematic = planMotionTransition('panel_open', { intensity: 'cinematic' });
    const off = planMotionTransition('panel_open', { intensity: 'off' });
    expect(subtle.durationMs).toBeGreaterThan(0);
    expect(cinematic.durationMs).toBeGreaterThan(subtle.durationMs);
    expect(off.durationMs).toBe(0);
    expect(off.cameraDolly).toBe(false);
  });

  it('honors reduced motion and settles alerts', () => {
    const reduced = planMotionTransition('node_select', { reducedMotion: true });
    expect(reduced.durationMs).toBe(0);
    const alert = planMotionTransition('alert_sweep', { intensity: 'cinematic' });
    expect(alert.settleOnly).toBe(true);
  });

  it('parses intensity storage values', () => {
    expect(motionIntensityFromStorage('cinematic')).toBe('cinematic');
    expect(motionIntensityFromStorage('nope')).toBe('subtle');
  });
});
