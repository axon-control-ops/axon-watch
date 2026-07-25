import { describe, expect, it } from 'vitest';

import {
  rectsOverlap,
  resolveAutoAvoidOrbCandidates,
  resolveDockPresetPosition,
  resolveSmartDodgeOrbPosition,
} from './kairo-galaxy-orb-position';

describe('kairo-galaxy-orb-position', () => {
  it('detects overlap between orb and conversation surface', () => {
    expect(
      rectsOverlap(
        { left: 10, top: 10, right: 110, bottom: 110 },
        { left: 80, top: 80, right: 180, bottom: 180 },
      ),
    ).toBe(true);
  });

  it('lifts the orb above the conversation panel before trying lateral moves', () => {
    const candidates = resolveAutoAvoidOrbCandidates({
      stage: { width: 640, height: 400 },
      orb: { width: 200, height: 192 },
      obstacle: { left: 12, top: 260, right: 628, bottom: 388 },
      margins: { left: 12, top: 56, right: 12, bottom: 94 },
      dockTopOffset: 48,
      clearance: 12,
    });

    expect(candidates[0]).toEqual({ x: 428, y: 104 });
    expect(candidates[1]).toEqual({ x: 12, y: 104 });
  });

  it('never falls back into the lower-left conversation area', () => {
    const candidates = resolveAutoAvoidOrbCandidates({
      stage: { width: 640, height: 400 },
      orb: { width: 200, height: 192 },
      obstacle: { left: 12, top: 280, right: 628, bottom: 388 },
      margins: { left: 12, top: 56, right: 12, bottom: 94 },
      dockTopOffset: 48,
      clearance: 12,
    });

    expect(candidates.every((candidate) => candidate.y <= 104)).toBe(true);
  });

  it('includes a stable top-right dock candidate', () => {
    const candidates = resolveAutoAvoidOrbCandidates({
      stage: { width: 640, height: 400 },
      orb: { width: 200, height: 192 },
      obstacle: { left: 12, top: 260, right: 628, bottom: 388 },
      margins: { left: 12, top: 56, right: 12, bottom: 94 },
      dockTopOffset: 48,
      clearance: 12,
    });

    expect(candidates[2]).toEqual({ x: 428, y: 104 });
  });

  it('resolves viewport dock presets', () => {
    const margins = { left: 12, top: 56, right: 12, bottom: 48 };
    const viewport = { width: 1200, height: 800 };
    const orb = { width: 200, height: 240 };
    expect(resolveDockPresetPosition({ dock: 'top-left', viewport, orb, margins })).toEqual({
      x: 12,
      y: 56,
    });
    expect(resolveDockPresetPosition({ dock: 'bottom-right', viewport, orb, margins })).toEqual({
      x: 988,
      y: 512,
    });
  });

  it('smart-dodges to a clear dock when the preferred corner is blocked', () => {
    const margins = { left: 12, top: 56, right: 12, bottom: 48 };
    const viewport = { width: 1200, height: 800 };
    const orb = { width: 200, height: 240 };
    const result = resolveSmartDodgeOrbPosition({
      viewport,
      orb,
      margins,
      preferredDock: 'top-right',
      obstacles: [{ left: 900, top: 0, right: 1200, bottom: 400 }],
    });
    expect(result.dock).toBe('top-left');
    expect(result.position).toEqual({ x: 12, y: 56 });
  });
});
