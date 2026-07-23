import type { OrbBoxSize, OrbMargins, OrbPosition, OrbRect } from './kairo-galaxy-orb-position';
import {
  clampOrbToViewport,
  positionOverlapsAny,
  resolveDockPresetPosition,
  resolveSmartDodgeOrbPosition,
} from './kairo-galaxy-orb-position';

export const VOICE_ORB_VIEWPORT_STORAGE_KEY = 'axon-x:vaxon-orb-viewport';

export type VoiceOrbDock =
  | 'top-left'
  | 'top-right'
  | 'bottom-left'
  | 'bottom-right'
  | 'center';

export type VoiceOrbPlacementState = {
  dock: VoiceOrbDock | 'custom';
  x: number;
  y: number;
  userPinned: boolean;
  visible?: boolean;
};

export const DEFAULT_VOICE_ORB_DOCK: VoiceOrbDock = 'top-right';

export const VOICE_ORB_VIEWPORT_MARGINS: OrbMargins = {
  left: 12,
  top: 56,
  right: 12,
  bottom: 48,
};

/** Known console chrome selectors used for smart-dodge obstacles. */
export const VOICE_ORB_OBSTACLE_SELECTORS = [
  '.region-topbar',
  '.region-status-bar',
  '.region-left-sidebar',
  '.region-right-dock',
  '.agent-dock',
  '.center-workbench__terminal-panel',
  '.brain-galaxy-stage__hud--bottom',
  '.brain-galaxy-stage__hud--left',
  '.brain-galaxy-stage__hud--right',
  '.brain-galaxy-stage__hud--inspector',
  '.brain-galaxy-stage__hud--top',
  '.galaxy-ambient-hud',
  '.mobile-voice-cockpit-strip',
  /* Keep the floating orb off Fleet / Task mosaic content. */
  '[data-orb-obstacle="mission"]',
  '.operator-fleet-grid-host',
  '.operator-task-board-host',
] as const;

export function normalizeVoiceOrbDock(value: unknown): VoiceOrbDock | null {
  const raw = String(value ?? '')
    .trim()
    .toLowerCase()
    .replace(/_/g, '-');
  if (
    raw === 'top-left' ||
    raw === 'top-right' ||
    raw === 'bottom-left' ||
    raw === 'bottom-right' ||
    raw === 'center'
  ) {
    return raw;
  }
  return null;
}

export function parsePersistedVoiceOrbPlacement(raw: string | null): VoiceOrbPlacementState | null {
  if (!raw) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as {
      dock?: unknown;
      x?: unknown;
      y?: unknown;
      userPinned?: unknown;
      visible?: unknown;
    };
    if (typeof parsed.x !== 'number' || typeof parsed.y !== 'number') {
      return null;
    }
    const dock = normalizeVoiceOrbDock(parsed.dock) ?? 'custom';
    return {
      dock: parsed.dock === 'custom' ? 'custom' : dock,
      x: parsed.x,
      y: parsed.y,
      userPinned: parsed.userPinned === true,
      visible: parsed.visible !== false,
    };
  } catch {
    return null;
  }
}

export function serializeVoiceOrbPlacement(state: VoiceOrbPlacementState): string {
  return JSON.stringify(state);
}

export function readVoiceOrbPlacementFromStorage(
  storage: Pick<Storage, 'getItem'> | null | undefined = typeof localStorage !== 'undefined'
    ? localStorage
    : null,
): VoiceOrbPlacementState | null {
  if (!storage) {
    return null;
  }
  return parsePersistedVoiceOrbPlacement(storage.getItem(VOICE_ORB_VIEWPORT_STORAGE_KEY));
}

export function writeVoiceOrbPlacementToStorage(
  state: VoiceOrbPlacementState,
  storage: Pick<Storage, 'setItem'> | null | undefined = typeof localStorage !== 'undefined'
    ? localStorage
    : null,
): void {
  if (!storage) {
    return;
  }
  storage.setItem(VOICE_ORB_VIEWPORT_STORAGE_KEY, serializeVoiceOrbPlacement(state));
}

export function collectObstacleRects(
  root: ParentNode | null | undefined,
  selectors: readonly string[] = VOICE_ORB_OBSTACLE_SELECTORS,
): OrbRect[] {
  if (!root || typeof (root as Document).querySelectorAll !== 'function') {
    return [];
  }
  const rects: OrbRect[] = [];
  for (const selector of selectors) {
    const nodes = root.querySelectorAll(selector);
    nodes.forEach((node) => {
      if (!(node instanceof HTMLElement)) {
        return;
      }
      const box = node.getBoundingClientRect();
      if (box.width < 8 || box.height < 8) {
        return;
      }
      rects.push({
        left: box.left,
        top: box.top,
        right: box.right,
        bottom: box.bottom,
      });
    });
  }
  return rects;
}

export function resolvePlacementForDock(options: {
  dock: VoiceOrbDock;
  viewport: OrbBoxSize;
  orb: OrbBoxSize;
  margins?: OrbMargins;
}): OrbPosition {
  return resolveDockPresetPosition({
    dock: options.dock,
    viewport: options.viewport,
    orb: options.orb,
    margins: options.margins ?? VOICE_ORB_VIEWPORT_MARGINS,
  });
}

export function resolveSmartDodgePlacement(options: {
  viewport: OrbBoxSize;
  orb: OrbBoxSize;
  obstacles: OrbRect[];
  preferredDock?: VoiceOrbDock;
  margins?: OrbMargins;
}): { position: OrbPosition; dock: VoiceOrbDock } {
  const margins = options.margins ?? VOICE_ORB_VIEWPORT_MARGINS;
  const result = resolveSmartDodgeOrbPosition({
    viewport: options.viewport,
    orb: options.orb,
    obstacles: options.obstacles,
    margins,
    preferredDock: options.preferredDock ?? DEFAULT_VOICE_ORB_DOCK,
  });
  return result;
}

export function clampPlacementToViewport(options: {
  position: OrbPosition;
  viewport: OrbBoxSize;
  orb: OrbBoxSize;
  margins?: OrbMargins;
}): OrbPosition {
  return clampOrbToViewport({
    position: options.position,
    viewport: options.viewport,
    orb: options.orb,
    margins: options.margins ?? VOICE_ORB_VIEWPORT_MARGINS,
  });
}

export function placementOverlapsObstacles(
  position: OrbPosition,
  orb: OrbBoxSize,
  obstacles: OrbRect[],
): boolean {
  return positionOverlapsAny(position, orb, obstacles);
}
