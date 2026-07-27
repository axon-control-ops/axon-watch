export const GALAXY_PANEL_WIDTHS_KEY = 'axon-x-galaxy-panel-widths-v1';
export const GALAXY_WORKSPACES_COLLAPSED_KEY = 'axon-x-galaxy-workspaces-collapsed-v1';
/** Narrow strip width when the Brain Graph workspaces rail is collapsed. */
export const GALAXY_LEFT_COLLAPSED_WIDTH_PX = 44;

export type GalaxyPanelKind = 'left' | 'right' | 'inspector';

export type GalaxyPanelWidths = {
  left: number;
  right: number;
  inspector: number;
};

export const GALAXY_PANEL_DEFAULTS: GalaxyPanelWidths = {
  left: 264,
  right: 240,
  inspector: 368,
};

export const GALAXY_PANEL_MIN: GalaxyPanelWidths = {
  left: 180,
  right: 180,
  inspector: 260,
};

export const GALAXY_PANEL_MAX: GalaxyPanelWidths = {
  left: 420,
  right: 360,
  inspector: 520,
};

export const GALAXY_PANEL_STEP_PX = 16;
export const GALAXY_PANEL_STEP_LARGE_PX = 48;

export function maxGalaxyPanelWidth(
  kind: GalaxyPanelKind,
  viewportWidth: number,
): number {
  const hardMax = GALAXY_PANEL_MAX[kind];
  if (!Number.isFinite(viewportWidth) || viewportWidth <= 0) {
    return hardMax;
  }
  // Leave room for the opposite rail + center galaxy stage.
  const budget =
    kind === 'left'
      ? Math.floor(viewportWidth * 0.36)
      : kind === 'right'
        ? Math.floor(viewportWidth * 0.3)
        : Math.floor(viewportWidth * 0.4);
  return Math.max(GALAXY_PANEL_MIN[kind], Math.min(hardMax, budget));
}

export function clampGalaxyPanelWidth(
  kind: GalaxyPanelKind,
  width: number,
  viewportWidth: number,
): number {
  if (!Number.isFinite(width)) {
    return GALAXY_PANEL_DEFAULTS[kind];
  }
  const max = maxGalaxyPanelWidth(kind, viewportWidth);
  return Math.min(max, Math.max(GALAXY_PANEL_MIN[kind], Math.round(width)));
}

export function defaultGalaxyPanelWidths(viewportWidth: number): GalaxyPanelWidths {
  return {
    left: clampGalaxyPanelWidth('left', GALAXY_PANEL_DEFAULTS.left, viewportWidth),
    right: clampGalaxyPanelWidth('right', GALAXY_PANEL_DEFAULTS.right, viewportWidth),
    inspector: clampGalaxyPanelWidth(
      'inspector',
      GALAXY_PANEL_DEFAULTS.inspector,
      viewportWidth,
    ),
  };
}

export function readStoredGalaxyPanelWidths(): Partial<GalaxyPanelWidths> | null {
  if (typeof window === 'undefined') {
    return null;
  }
  const raw = window.localStorage.getItem(GALAXY_PANEL_WIDTHS_KEY);
  if (!raw) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as Partial<GalaxyPanelWidths>;
    if (!parsed || typeof parsed !== 'object') {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function persistGalaxyPanelWidths(widths: GalaxyPanelWidths): void {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.setItem(GALAXY_PANEL_WIDTHS_KEY, JSON.stringify(widths));
}

/** Default expanded so existing Brain Graph users keep the full rail. */
export function readStoredGalaxyWorkspacesCollapsed(): boolean {
  if (typeof window === 'undefined') {
    return false;
  }
  const raw = window.localStorage.getItem(GALAXY_WORKSPACES_COLLAPSED_KEY);
  return raw === '1' || raw === 'true';
}

export function persistGalaxyWorkspacesCollapsed(collapsed: boolean): void {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.setItem(
    GALAXY_WORKSPACES_COLLAPSED_KEY,
    collapsed ? '1' : '0',
  );
}

export type GalaxyPanelResizeKeyAction =
  | { type: 'nudge'; delta: number }
  | { type: 'min' }
  | { type: 'max' }
  | { type: 'reset' };

export function resolveGalaxyPanelResizeKey(
  key: string,
  shiftKey: boolean,
  edge: 'left' | 'right',
): GalaxyPanelResizeKeyAction | null {
  const step = shiftKey ? GALAXY_PANEL_STEP_LARGE_PX : GALAXY_PANEL_STEP_PX;
  // Left-edge handle: ArrowRight widens. Right-edge handle: ArrowLeft widens.
  if (key === 'ArrowLeft') {
    return { type: 'nudge', delta: edge === 'right' ? step : -step };
  }
  if (key === 'ArrowRight') {
    return { type: 'nudge', delta: edge === 'right' ? -step : step };
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

export function applyGalaxyPanelResizeKeyAction(
  kind: GalaxyPanelKind,
  width: number,
  action: GalaxyPanelResizeKeyAction,
  viewportWidth: number,
): number {
  if (action.type === 'nudge') {
    return clampGalaxyPanelWidth(kind, width + action.delta, viewportWidth);
  }
  if (action.type === 'min') {
    return clampGalaxyPanelWidth(kind, GALAXY_PANEL_MIN[kind], viewportWidth);
  }
  if (action.type === 'max') {
    return clampGalaxyPanelWidth(
      kind,
      maxGalaxyPanelWidth(kind, viewportWidth),
      viewportWidth,
    );
  }
  return clampGalaxyPanelWidth(kind, GALAXY_PANEL_DEFAULTS[kind], viewportWidth);
}
