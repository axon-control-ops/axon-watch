export type OrbRect = {
  left: number;
  top: number;
  right: number;
  bottom: number;
};

export type OrbBoxSize = {
  width: number;
  height: number;
};

export type OrbMargins = {
  left: number;
  top: number;
  right: number;
  bottom: number;
};

export type OrbPosition = {
  x: number;
  y: number;
};

export type OrbDockPreset =
  | 'top-left'
  | 'top-right'
  | 'bottom-left'
  | 'bottom-right'
  | 'center';

export function rectsOverlap(a: OrbRect, b: OrbRect): boolean {
  return !(a.right < b.left || a.left > b.right || a.bottom < b.top || a.top > b.bottom);
}

export function orbRectFromPosition(position: OrbPosition, orb: OrbBoxSize): OrbRect {
  return {
    left: position.x,
    top: position.y,
    right: position.x + orb.width,
    bottom: position.y + orb.height,
  };
}

export function positionOverlapsAny(
  position: OrbPosition,
  orb: OrbBoxSize,
  obstacles: OrbRect[],
): boolean {
  const self = orbRectFromPosition(position, orb);
  return obstacles.some((obstacle) => rectsOverlap(self, obstacle));
}

function clampPosition(
  position: OrbPosition,
  stage: OrbBoxSize,
  orb: OrbBoxSize,
  margins: OrbMargins,
): OrbPosition {
  const maxX = Math.max(margins.left, stage.width - orb.width - margins.right);
  const maxY = Math.max(margins.top, stage.height - orb.height - margins.bottom);
  return {
    x: Math.min(Math.max(position.x, margins.left), maxX),
    y: Math.min(Math.max(position.y, margins.top), maxY),
  };
}

export function clampOrbToViewport(options: {
  position: OrbPosition;
  viewport: OrbBoxSize;
  orb: OrbBoxSize;
  margins: OrbMargins;
}): OrbPosition {
  return clampPosition(options.position, options.viewport, options.orb, options.margins);
}

/** Legacy single-HUD auto-avoid (stage-local). Kept for existing tests. */
export function resolveAutoAvoidOrbCandidates(options: {
  stage: OrbBoxSize;
  orb: OrbBoxSize;
  obstacle: OrbRect;
  margins: OrbMargins;
  dockTopOffset: number;
  clearance: number;
}): OrbPosition[] {
  const { stage, orb, obstacle, margins, dockTopOffset, clearance } = options;
  const rightDockX = stage.width - orb.width - margins.right;
  const leftDockX = margins.left;
  const topDockY = margins.top + dockTopOffset;
  const safeTopY = obstacle.top - orb.height - clearance;
  const liftedY = Math.max(topDockY, safeTopY);

  return [
    clampPosition({ x: rightDockX, y: liftedY }, stage, orb, margins),
    clampPosition({ x: leftDockX, y: liftedY }, stage, orb, margins),
    clampPosition({ x: rightDockX, y: topDockY }, stage, orb, margins),
  ];
}

export function resolveDockPresetPosition(options: {
  dock: OrbDockPreset;
  viewport: OrbBoxSize;
  orb: OrbBoxSize;
  margins: OrbMargins;
}): OrbPosition {
  const { dock, viewport, orb, margins } = options;
  const left = margins.left;
  const right = Math.max(margins.left, viewport.width - orb.width - margins.right);
  const top = margins.top;
  const bottom = Math.max(margins.top, viewport.height - orb.height - margins.bottom);
  const centerX = Math.max(left, Math.min(right, (viewport.width - orb.width) / 2));
  const centerY = Math.max(top, Math.min(bottom, (viewport.height - orb.height) / 2));

  switch (dock) {
    case 'top-left':
      return clampPosition({ x: left, y: top }, viewport, orb, margins);
    case 'bottom-left':
      return clampPosition({ x: left, y: bottom }, viewport, orb, margins);
    case 'bottom-right':
      return clampPosition({ x: right, y: bottom }, viewport, orb, margins);
    case 'center':
      return clampPosition({ x: centerX, y: centerY }, viewport, orb, margins);
    case 'top-right':
    default:
      return clampPosition({ x: right, y: top }, viewport, orb, margins);
  }
}

function overlapArea(a: OrbRect, b: OrbRect): number {
  const width = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
  const height = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
  return width * height;
}

function totalOverlapArea(position: OrbPosition, orb: OrbBoxSize, obstacles: OrbRect[]): number {
  const self = orbRectFromPosition(position, orb);
  return obstacles.reduce((sum, obstacle) => sum + overlapArea(self, obstacle), 0);
}

const DOCK_ORDER: OrbDockPreset[] = [
  'top-right',
  'top-left',
  'bottom-right',
  'bottom-left',
  'center',
];

export function resolveSmartDodgeOrbPosition(options: {
  viewport: OrbBoxSize;
  orb: OrbBoxSize;
  obstacles: OrbRect[];
  margins: OrbMargins;
  preferredDock?: OrbDockPreset;
}): { position: OrbPosition; dock: OrbDockPreset } {
  const preferred = options.preferredDock ?? 'top-right';
  const ordered = [preferred, ...DOCK_ORDER.filter((dock) => dock !== preferred)];
  let best: { position: OrbPosition; dock: OrbDockPreset; score: number } | null = null;

  for (const dock of ordered) {
    const position = resolveDockPresetPosition({
      dock,
      viewport: options.viewport,
      orb: options.orb,
      margins: options.margins,
    });
    const score = totalOverlapArea(position, options.orb, options.obstacles);
    if (score === 0) {
      return { position, dock };
    }
    if (!best || score < best.score) {
      best = { position, dock, score };
    }
  }

  return {
    position: best?.position ?? resolveDockPresetPosition({
      dock: preferred,
      viewport: options.viewport,
      orb: options.orb,
      margins: options.margins,
    }),
    dock: best?.dock ?? preferred,
  };
}

/** Multi-obstacle candidate list (preferred docks first). */
export function resolveViewportDodgeCandidates(options: {
  viewport: OrbBoxSize;
  orb: OrbBoxSize;
  obstacles: OrbRect[];
  margins: OrbMargins;
  preferredDock?: OrbDockPreset;
}): OrbPosition[] {
  const preferred = options.preferredDock ?? 'top-right';
  const ordered = [preferred, ...DOCK_ORDER.filter((dock) => dock !== preferred)];
  return ordered.map((dock) =>
    resolveDockPresetPosition({
      dock,
      viewport: options.viewport,
      orb: options.orb,
      margins: options.margins,
    }),
  );
}
