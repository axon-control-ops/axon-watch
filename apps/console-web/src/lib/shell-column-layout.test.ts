import { describe, expect, it } from 'vitest';

import {
  computeBriefingDockHeight,
  computeShellColumnMinHeight,
  isShellLayoutGeometrySane,
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

  it('scales briefing dock height below terminal dock height', () => {
    expect(computeBriefingDockHeight(367)).toBe(301);
    expect(computeBriefingDockHeight(0)).toBe(0);
    expect(computeBriefingDockHeight(120)).toBe(152);
  });
});
