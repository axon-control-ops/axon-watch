/** Viewport-clamped placement for menus teleported out of their stacking context. */

export interface FloatingAnchorRect {
  right: number;
  bottom: number;
}

export interface FloatingViewport {
  width: number;
  height: number;
}

export interface FloatingPanelPlacement {
  top: number;
  left: number;
  maxHeight: number;
}

export const FLOATING_PANEL_GAP_PX = 6;
export const FLOATING_VIEWPORT_MARGIN_PX = 8;
const FLOATING_MIN_PANEL_HEIGHT_PX = 160;

/**
 * Right-align a panel to its trigger, clamped inside the viewport.
 *
 * Kept pure so the clamping is testable: the panel is rendered in <body> via
 * Teleport (the topbar's stacking context would otherwise bury it), which
 * means CSS can no longer keep it on screen and these numbers are the only
 * thing preventing an off-viewport menu.
 */
export function floatingPanelPlacement(
  anchor: FloatingAnchorRect,
  panelWidth: number,
  viewport: FloatingViewport,
  options?: { gap?: number; margin?: number },
): FloatingPanelPlacement {
  const gap = options?.gap ?? FLOATING_PANEL_GAP_PX;
  const margin = options?.margin ?? FLOATING_VIEWPORT_MARGIN_PX;

  const maxLeft = viewport.width - panelWidth - margin;
  // Math.min first (prefer right-aligned to the trigger, pull left if it would
  // overflow), then Math.max so a panel wider than the viewport still starts
  // at the margin instead of going negative.
  const left = Math.max(margin, Math.min(anchor.right - panelWidth, maxLeft));
  const top = anchor.bottom + gap;
  const maxHeight = Math.max(
    FLOATING_MIN_PANEL_HEIGHT_PX,
    Math.round(viewport.height - top - margin),
  );

  return { top: Math.round(top), left: Math.round(left), maxHeight };
}
