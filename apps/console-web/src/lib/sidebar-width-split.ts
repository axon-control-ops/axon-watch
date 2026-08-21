export const SIDEBAR_WIDTH_KEY = 'axon-x-left-sidebar-width-v1';
export const DEFAULT_SIDEBAR_WIDTH = 340;
export const MIN_SIDEBAR_WIDTH = 240;
export const MAX_SIDEBAR_WIDTH = 480;

export function clampSidebarWidth(width: number, viewportWidth: number): number {
  if (!Number.isFinite(width) || viewportWidth <= 0) {
    return DEFAULT_SIDEBAR_WIDTH;
  }

  // 0.34 of viewport is the intended secondary cap on narrow screens; on a
  // typical 1400px viewport that alone floors to 476, one below the 480
  // MAX_SIDEBAR_WIDTH raised for higher-density displays -- so the exported
  // maximum was never actually reachable. 0.36 clears 480 at 1400px while
  // still capping well below it on genuinely narrow viewports.
  const maxWidth = Math.min(
    MAX_SIDEBAR_WIDTH,
    Math.max(MIN_SIDEBAR_WIDTH, Math.floor(viewportWidth * 0.36)),
  );
  return Math.min(maxWidth, Math.max(MIN_SIDEBAR_WIDTH, Math.round(width)));
}

export function readStoredSidebarWidth(): number | null {
  if (typeof window === 'undefined') {
    return null;
  }

  const raw = window.sessionStorage.getItem(SIDEBAR_WIDTH_KEY);
  if (!raw) {
    return null;
  }

  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}
