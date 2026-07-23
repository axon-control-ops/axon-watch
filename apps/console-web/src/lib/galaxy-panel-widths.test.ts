import { describe, expect, it } from 'vitest';

import {
  applyGalaxyPanelResizeKeyAction,
  clampGalaxyPanelWidth,
  resolveGalaxyPanelResizeKey,
} from './galaxy-panel-widths';

describe('galaxy-panel-widths', () => {
  it('clamps panel widths within viewport budget', () => {
    expect(clampGalaxyPanelWidth('left', 900, 1280)).toBeLessThanOrEqual(420);
    expect(clampGalaxyPanelWidth('inspector', 100, 1280)).toBe(260);
    expect(clampGalaxyPanelWidth('right', 240, 1280)).toBe(240);
  });

  it('maps keyboard actions for left and right edges', () => {
    expect(resolveGalaxyPanelResizeKey('ArrowRight', false, 'left')).toEqual({
      type: 'nudge',
      delta: 16,
    });
    expect(resolveGalaxyPanelResizeKey('ArrowLeft', false, 'right')).toEqual({
      type: 'nudge',
      delta: 16,
    });
    expect(resolveGalaxyPanelResizeKey('Enter', false, 'left')).toEqual({
      type: 'reset',
    });
  });

  it('applies reset to defaults', () => {
    expect(
      applyGalaxyPanelResizeKeyAction('inspector', 500, { type: 'reset' }, 1440),
    ).toBe(368);
  });
});
