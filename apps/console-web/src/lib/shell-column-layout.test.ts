import { describe, expect, it } from 'vitest';

import {
  computeBriefingDockHeight,
  computeHeroDockHeight,
  computeShellColumnMinHeight,
  isShellLayoutGeometrySane,
  OPERATOR_HERO_DOCK_HEIGHT_PX,
  parseCssLengthPx,
} from './shell-column-layout';

describe('shell column layout helpers', () => {
  it('parses rem and px gutter values', () => {
    expect(parseCssLengthPx('0.85rem', 16)).toBe(13.6);
    expect(parseCssLengthPx('13.6px')).toBe(13.6);
  });

  it('reserves footer seam gap above the status bar', () => {
    expect(computeShellColumnMinHeight(100, 900, 13.6)).toBe(786.4);
    expect(computeShellColumnMinHeight(100, 900, 10.4)).toBe(789.6);
  });

  it('never returns negative heights', () => {
    expect(computeShellColumnMinHeight(890, 900, 12)).toBe(0);
  });

  it('rejects offscreen geometry during HMR', () => {
    expect(isShellLayoutGeometrySane(3_358_000, 3_356_000, 900)).toBe(false);
    expect(isShellLayoutGeometrySane(72, 920, 900)).toBe(true);
  });

  it('uses a fixed compact hero height in operator mode', () => {
    expect(computeHeroDockHeight(367, 'operator')).toBe(OPERATOR_HERO_DOCK_HEIGHT_PX);
    expect(computeHeroDockHeight(120, 'operator')).toBe(OPERATOR_HERO_DOCK_HEIGHT_PX);
  });

  it('scales IDE hero height below terminal dock height with a cap', () => {
    expect(computeHeroDockHeight(367, 'ide')).toBe(154);
    expect(computeHeroDockHeight(0, 'ide')).toBe(128);
    expect(computeHeroDockHeight(120, 'ide')).toBe(128);
    expect(computeHeroDockHeight(900, 'ide')).toBe(176);
    expect(computeBriefingDockHeight(367)).toBe(154);
  });
});
