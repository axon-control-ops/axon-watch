export const WORKBENCH_TERMINAL_HEIGHT_KEY = 'axon-x-workbench-terminal-height-v3';
export const WORKBENCH_TERMINAL_PANEL_VISIBLE_KEY = 'axon-x-workbench-terminal-panel-visible-v1';
export const DEFAULT_WORKBENCH_TERMINAL_HEIGHT = 240;
export const DEFAULT_WORKBENCH_TERMINAL_HEIGHT_RATIO = 0.26;
export const MAX_DEFAULT_WORKBENCH_TERMINAL_HEIGHT = 280;
export const MIN_WORKBENCH_TERMINAL_HEIGHT = 176;
export const MAX_WORKBENCH_TERMINAL_RATIO = 0.88;
export const WORKBENCH_TERMINAL_RESIZE_HANDLE_HEIGHT = 6;

export function resolveDefaultWorkbenchTerminalHeight(containerHeight: number): number {
  if (!Number.isFinite(containerHeight) || containerHeight <= 0) {
    return DEFAULT_WORKBENCH_TERMINAL_HEIGHT;
  }

  const ratioHeight = Math.round(containerHeight * DEFAULT_WORKBENCH_TERMINAL_HEIGHT_RATIO);
  const target = Math.min(
    MAX_DEFAULT_WORKBENCH_TERMINAL_HEIGHT,
    Math.max(DEFAULT_WORKBENCH_TERMINAL_HEIGHT, ratioHeight),
  );
  return clampWorkbenchTerminalHeight(target, containerHeight);
}

export function clampWorkbenchTerminalHeight(
  height: number,
  containerHeight: number,
): number {
  if (!Number.isFinite(height) || containerHeight <= 0) {
    return DEFAULT_WORKBENCH_TERMINAL_HEIGHT;
  }

  const maxHeight = Math.max(
    MIN_WORKBENCH_TERMINAL_HEIGHT,
    Math.floor(containerHeight * MAX_WORKBENCH_TERMINAL_RATIO),
  );
  return Math.min(maxHeight, Math.max(MIN_WORKBENCH_TERMINAL_HEIGHT, Math.round(height)));
}

export function readStoredWorkbenchTerminalHeight(): number | null {
  if (typeof window === 'undefined') {
    return null;
  }

  const raw = window.sessionStorage.getItem(WORKBENCH_TERMINAL_HEIGHT_KEY);
  if (!raw) {
    return null;
  }

  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

export function readStoredWorkbenchTerminalPanelVisible(): boolean {
  if (typeof window === 'undefined') {
    return true;
  }

  const raw = window.sessionStorage.getItem(WORKBENCH_TERMINAL_PANEL_VISIBLE_KEY);
  if (raw === '0' || raw === 'false') {
    return false;
  }

  return true;
}
