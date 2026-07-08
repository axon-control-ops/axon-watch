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

export function rectsOverlap(a: OrbRect, b: OrbRect): boolean {
  return !(a.right < b.left || a.left > b.right || a.bottom < b.top || a.top > b.bottom);
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
