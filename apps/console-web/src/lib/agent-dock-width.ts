export const AGENT_DOCK_WIDTH_KEY = 'axon-x-agent-dock-width-v1';
export const DEFAULT_AGENT_DOCK_WIDTH = 380;
export const MIN_AGENT_DOCK_WIDTH = 280;
export const MAX_AGENT_DOCK_WIDTH = 720;
export const AGENT_DOCK_COLLAPSED_WIDTH_PX = 36;

export function clampAgentDockWidth(width: number, viewportWidth: number): number {
  if (!Number.isFinite(width) || viewportWidth <= 0) {
    return DEFAULT_AGENT_DOCK_WIDTH;
  }

  const maxWidth = Math.max(
    MIN_AGENT_DOCK_WIDTH,
    Math.min(MAX_AGENT_DOCK_WIDTH, viewportWidth - 480),
  );
  return Math.min(maxWidth, Math.max(MIN_AGENT_DOCK_WIDTH, Math.round(width)));
}

export function defaultAgentDockWidth(viewportWidth: number): number {
  const target = Math.round(viewportWidth * 0.32);
  return clampAgentDockWidth(target, viewportWidth);
}

export function readStoredAgentDockWidth(): number | null {
  if (typeof window === 'undefined') {
    return null;
  }

  const raw = window.localStorage.getItem(AGENT_DOCK_WIDTH_KEY);
  if (!raw) {
    return null;
  }

  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

export function persistAgentDockWidth(width: number): void {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.setItem(AGENT_DOCK_WIDTH_KEY, String(width));
}
