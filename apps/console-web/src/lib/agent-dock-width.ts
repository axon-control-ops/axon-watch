export const AGENT_DOCK_WIDTH_KEY = 'axon-x-agent-dock-width-v1';
export const DEFAULT_AGENT_DOCK_WIDTH = 380;
export const MIN_AGENT_DOCK_WIDTH = 280;
export const MAX_AGENT_DOCK_WIDTH = 720;
export const AGENT_DOCK_COLLAPSED_WIDTH_PX = 36;
export const AGENT_DOCK_WIDTH_STEP_PX = 16;
export const AGENT_DOCK_WIDTH_STEP_LARGE_PX = 48;

export function maxAgentDockWidth(viewportWidth: number): number {
  if (!Number.isFinite(viewportWidth) || viewportWidth <= 0) {
    return MAX_AGENT_DOCK_WIDTH;
  }

  return Math.max(
    MIN_AGENT_DOCK_WIDTH,
    Math.min(MAX_AGENT_DOCK_WIDTH, viewportWidth - 480),
  );
}

export function clampAgentDockWidth(width: number, viewportWidth: number): number {
  if (!Number.isFinite(width) || viewportWidth <= 0) {
    return DEFAULT_AGENT_DOCK_WIDTH;
  }

  const maxWidth = maxAgentDockWidth(viewportWidth);
  return Math.min(maxWidth, Math.max(MIN_AGENT_DOCK_WIDTH, Math.round(width)));
}

export function defaultAgentDockWidth(viewportWidth: number): number {
  const target = Math.round(viewportWidth * 0.32);
  return clampAgentDockWidth(target, viewportWidth);
}

/** Nudge dock width; positive delta widens the right dock. */
export function nudgeAgentDockWidth(
  width: number,
  delta: number,
  viewportWidth: number,
): number {
  if (!Number.isFinite(delta)) {
    return clampAgentDockWidth(width, viewportWidth);
  }

  return clampAgentDockWidth(width + delta, viewportWidth);
}

export type AgentDockResizeKeyAction =
  | { type: 'nudge'; delta: number }
  | { type: 'min' }
  | { type: 'max' }
  | { type: 'reset' };

/** Map keyboard input on the dock resize separator to a width action. */
export function resolveAgentDockResizeKey(
  key: string,
  shiftKey: boolean,
): AgentDockResizeKeyAction | null {
  const step = shiftKey ? AGENT_DOCK_WIDTH_STEP_LARGE_PX : AGENT_DOCK_WIDTH_STEP_PX;

  if (key === 'ArrowLeft') {
    return { type: 'nudge', delta: step };
  }

  if (key === 'ArrowRight') {
    return { type: 'nudge', delta: -step };
  }

  if (key === 'Home') {
    return { type: 'min' };
  }

  if (key === 'End') {
    return { type: 'max' };
  }

  if (key === 'Enter') {
    return { type: 'reset' };
  }

  return null;
}

export function applyAgentDockResizeKeyAction(
  width: number,
  action: AgentDockResizeKeyAction,
  viewportWidth: number,
): number {
  if (action.type === 'nudge') {
    return nudgeAgentDockWidth(width, action.delta, viewportWidth);
  }

  if (action.type === 'min') {
    return clampAgentDockWidth(MIN_AGENT_DOCK_WIDTH, viewportWidth);
  }

  if (action.type === 'max') {
    return clampAgentDockWidth(maxAgentDockWidth(viewportWidth), viewportWidth);
  }

  return defaultAgentDockWidth(viewportWidth);
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
