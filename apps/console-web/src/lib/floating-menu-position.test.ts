import { describe, expect, it } from 'vitest';

import {
  FLOATING_PANEL_DESIGN_MAX_HEIGHT_PX,
  FLOATING_PANEL_GAP_PX,
  FLOATING_VIEWPORT_MARGIN_PX,
  floatingPanelPlacement,
} from './floating-menu-position';

const VIEWPORT = { width: 1920, height: 1080 };
const PANEL_WIDTH = 216;

describe('floatingPanelPlacement', () => {
  it('right-aligns the panel to its trigger and sits just below it', () => {
    const placement = floatingPanelPlacement(
      { right: 1300, bottom: 176 },
      PANEL_WIDTH,
      VIEWPORT,
    );
    expect(placement.left).toBe(1300 - PANEL_WIDTH);
    expect(placement.top).toBe(176 + FLOATING_PANEL_GAP_PX);
  });

  it('clamps a right-edge trigger so the panel stays on screen', () => {
    const placement = floatingPanelPlacement(
      { right: VIEWPORT.width, bottom: 100 },
      PANEL_WIDTH,
      VIEWPORT,
    );
    expect(placement.left).toBeLessThanOrEqual(
      VIEWPORT.width - PANEL_WIDTH - FLOATING_VIEWPORT_MARGIN_PX,
    );
    expect(placement.left).toBeGreaterThanOrEqual(FLOATING_VIEWPORT_MARGIN_PX);
  });

  it('never returns a negative left for a left-edge trigger', () => {
    const placement = floatingPanelPlacement({ right: 40, bottom: 100 }, PANEL_WIDTH, VIEWPORT);
    expect(placement.left).toBe(FLOATING_VIEWPORT_MARGIN_PX);
  });

  it('keeps a usable height when the trigger is near the bottom', () => {
    const placement = floatingPanelPlacement(
      { right: 800, bottom: VIEWPORT.height - 10 },
      PANEL_WIDTH,
      VIEWPORT,
    );
    expect(placement.maxHeight).toBeGreaterThanOrEqual(160);
  });

  it('never exceeds the designed max-height when there is ample room', () => {
    // Regression: an inline max-height beats the stylesheet's 13rem cap, so
    // without clamping the teleported panel grew to fill the viewport and the
    // 18-workspace list ran down the whole screen instead of scrolling.
    const placement = floatingPanelPlacement({ right: 800, bottom: 100 }, PANEL_WIDTH, VIEWPORT);
    expect(placement.maxHeight).toBe(FLOATING_PANEL_DESIGN_MAX_HEIGHT_PX);
  });

  it('shrinks below the design cap only when the trigger sits too low', () => {
    const roomy = floatingPanelPlacement({ right: 800, bottom: 100 }, PANEL_WIDTH, VIEWPORT);
    const tight = floatingPanelPlacement(
      { right: 800, bottom: VIEWPORT.height - 190 },
      PANEL_WIDTH,
      VIEWPORT,
    );
    expect(roomy.maxHeight).toBe(FLOATING_PANEL_DESIGN_MAX_HEIGHT_PX);
    expect(tight.maxHeight).toBeLessThan(roomy.maxHeight);
    expect(tight.maxHeight).toBeGreaterThanOrEqual(160);
  });

  it('handles a panel wider than the viewport without going off-screen left', () => {
    const placement = floatingPanelPlacement(
      { right: 300, bottom: 100 },
      900,
      { width: 500, height: 800 },
    );
    expect(placement.left).toBe(FLOATING_VIEWPORT_MARGIN_PX);
  });

  it('returns integers so no sub-pixel blur is introduced', () => {
    const placement = floatingPanelPlacement(
      { right: 1300.4, bottom: 176.7 },
      PANEL_WIDTH,
      VIEWPORT,
    );
    expect(Number.isInteger(placement.left)).toBe(true);
    expect(Number.isInteger(placement.top)).toBe(true);
    expect(Number.isInteger(placement.maxHeight)).toBe(true);
  });
});
