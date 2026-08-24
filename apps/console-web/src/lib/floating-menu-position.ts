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
 * The panel's designed cap (`max-height: 13rem` in ide-layout-03.css).
 *
 * An inline max-height beats the stylesheet, so without clamping to this the
 * teleported panel would grow to fill the viewport -- with 18 workspaces the
 * menu ballooned down the screen instead of scrolling inside its own box.
 */
export const FLOATING_PANEL_DESIGN_MAX_HEIGHT_PX = 208;

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
  options?: { gap?: number; margin?: number; designMaxHeight?: number },
): FloatingPanelPlacement {
  const gap = options?.gap ?? FLOATING_PANEL_GAP_PX;
  const margin = options?.margin ?? FLOATING_VIEWPORT_MARGIN_PX;
  const designMaxHeight = options?.designMaxHeight ?? FLOATING_PANEL_DESIGN_MAX_HEIGHT_PX;

  const maxLeft = viewport.width - panelWidth - margin;
  // Math.min first (prefer right-aligned to the trigger, pull left if it would
  // overflow), then Math.max so a panel wider than the viewport still starts
  // at the margin instead of going negative.
  const left = Math.max(margin, Math.min(anchor.right - panelWidth, maxLeft));
  const top = anchor.bottom + gap;
  // Never exceed the designed cap; only shrink below it when the trigger sits
  // too low for the panel to fit, and never below a usable minimum.
  const availableBelow = Math.round(viewport.height - top - margin);
  const maxHeight = Math.max(
    FLOATING_MIN_PANEL_HEIGHT_PX,
    Math.min(designMaxHeight, availableBelow),
  );

  return { top: Math.round(top), left: Math.round(left), maxHeight };
}
