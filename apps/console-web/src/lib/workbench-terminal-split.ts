export const WORKBENCH_TERMINAL_HEIGHT_KEY = 'axon-x-workbench-terminal-height-v3';
export const WORKBENCH_TERMINAL_PANEL_VISIBLE_KEY = 'axon-x-workbench-terminal-panel-visible-v1';
export const DEFAULT_WORKBENCH_TERMINAL_HEIGHT = 240;
export const DEFAULT_WORKBENCH_TERMINAL_HEIGHT_RATIO = 0.26;
export const OPERATOR_WORKBENCH_TERMINAL_HEIGHT_RATIO = 0.2;
export const MAX_DEFAULT_WORKBENCH_TERMINAL_HEIGHT = 280;
export const MIN_WORKBENCH_TERMINAL_HEIGHT = 176;
export const MAX_WORKBENCH_TERMINAL_RATIO = 0.88;
export const WORKBENCH_TERMINAL_RESIZE_HANDLE_HEIGHT = 6;

export type WorkbenchLayoutMode = 'operator' | 'ide';

export function workbenchTerminalPanelVisibleStorageKey(
  layoutMode: WorkbenchLayoutMode,
): string {
  return `${WORKBENCH_TERMINAL_PANEL_VISIBLE_KEY}:${layoutMode}`;
}

export function resolveDefaultWorkbenchTerminalHeight(
  containerHeight: number,
  layoutMode: WorkbenchLayoutMode = 'ide',
): number {
  if (!Number.isFinite(containerHeight) || containerHeight <= 0) {
    return DEFAULT_WORKBENCH_TERMINAL_HEIGHT;
  }

  const ratio =
    layoutMode === 'operator'
      ? OPERATOR_WORKBENCH_TERMINAL_HEIGHT_RATIO
      : DEFAULT_WORKBENCH_TERMINAL_HEIGHT_RATIO;
  const ratioHeight = Math.round(containerHeight * ratio);
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

export function readStoredWorkbenchTerminalPanelVisible(
  layoutMode: WorkbenchLayoutMode,
): boolean {
  const defaultVisible = layoutMode === 'ide';

  if (typeof window === 'undefined') {
    return defaultVisible;
  }

  const raw = window.sessionStorage.getItem(workbenchTerminalPanelVisibleStorageKey(layoutMode));
  if (raw === null) {
    return defaultVisible;
  }

  if (raw === '0' || raw === 'false') {
    return false;
  }

  return true;
}

export function persistWorkbenchTerminalPanelVisible(
  layoutMode: WorkbenchLayoutMode,
  visible: boolean,
): void {
  if (typeof window === 'undefined') {
    return;
  }

  window.sessionStorage.setItem(
    workbenchTerminalPanelVisibleStorageKey(layoutMode),
    visible ? '1' : '0',
  );
}
