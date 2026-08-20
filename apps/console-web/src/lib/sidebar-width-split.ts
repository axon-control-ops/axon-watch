export const SIDEBAR_WIDTH_KEY = 'axon-x-left-sidebar-width-v1';
export const DEFAULT_SIDEBAR_WIDTH = 340;
export const MIN_SIDEBAR_WIDTH = 240;
export const MAX_SIDEBAR_WIDTH = 480;

export function clampSidebarWidth(width: number, viewportWidth: number): number {
  if (!Number.isFinite(width) || viewportWidth <= 0) {
    return DEFAULT_SIDEBAR_WIDTH;
  }

  const maxWidth = Math.min(
    MAX_SIDEBAR_WIDTH,
    Math.max(MIN_SIDEBAR_WIDTH, Math.floor(viewportWidth * 0.34)),
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
