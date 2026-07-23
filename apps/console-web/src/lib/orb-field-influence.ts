/** Pure geometry for Mission Control cards reacting to the floating VAXON orb. */

export type OrbFieldBox = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export type OrbFieldElementBox = {
  left: number;
  top: number;
  width: number;
  height: number;
};

export type OrbFieldSample = {
  pushX: number;
  pushY: number;
  influence: number;
  localX: number;
  localY: number;
  biteR: number;
  scale: number;
  /** CSS border-radius tuned toward the orb when close. */
  radius: string;
  mask: boolean;
};

const DEFAULT_MAX_PUSH = 28;
const DEFAULT_SOFT_EXTRA = 36;

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export function orbVisualRadius(orb: Pick<OrbFieldBox, 'width' | 'height'>): number {
  return (Math.min(orb.width, orb.height) / 2) * 0.9;
}

export function orbCenter(orb: OrbFieldBox): { x: number; y: number } {
  return {
    x: orb.x + orb.width / 2,
    y: orb.y + orb.height / 2,
  };
}

/**
 * Sample how a rectangular card should yield around a circular orb.
 * Returns null when the orb is far enough that no motion/mask is needed.
 */
export function sampleOrbFieldInfluence(options: {
  orb: OrbFieldBox;
  element: OrbFieldElementBox;
  maxPush?: number;
  softExtra?: number;
}): OrbFieldSample | null {
  const maxPush = options.maxPush ?? DEFAULT_MAX_PUSH;
  const softExtra = options.softExtra ?? DEFAULT_SOFT_EXTRA;
  const center = orbCenter(options.orb);
  const radius = orbVisualRadius(options.orb);
  const elCx = options.element.left + options.element.width / 2;
  const elCy = options.element.top + options.element.height / 2;
  const dx = elCx - center.x;
  const dy = elCy - center.y;
  const dist = Math.hypot(dx, dy);
  const elementReach = Math.min(options.element.width, options.element.height) * 0.42;
  const clearance = radius + softExtra + elementReach;

  if (dist > clearance || clearance <= 0) {
    return null;
  }

  const overlap = clearance - dist;
  const influence = clamp(overlap / clearance, 0, 1);
  if (influence < 0.04) {
    return null;
  }

  const nx = dist > 0.001 ? dx / dist : 0;
  const ny = dist > 0.001 ? dy / dist : -1;
  const pushX = nx * maxPush * influence;
  const pushY = ny * maxPush * influence;
  const localX = center.x - options.element.left;
  const localY = center.y - options.element.top;
  const biteR = radius + 10 + influence * 18;
  const intersects =
    localX > -biteR &&
    localX < options.element.width + biteR &&
    localY > -biteR &&
    localY < options.element.height + biteR;

  const round = 0.35 + influence * 1.15;
  const radiusCss = `${(0.35 + influence * 0.55).toFixed(2)}rem ${round.toFixed(2)}rem ${(0.4 + influence * 0.7).toFixed(2)}rem ${(0.35 + influence * 0.45).toFixed(2)}rem / ${(0.4 + influence * 0.9).toFixed(2)}rem ${(0.35 + influence * 0.5).toFixed(2)}rem ${(0.45 + influence * 0.85).toFixed(2)}rem ${(0.35 + influence * 0.4).toFixed(2)}rem`;

  return {
    pushX,
    pushY,
    influence,
    localX,
    localY,
    biteR,
    scale: 1 - influence * 0.04,
    radius: radiusCss,
    mask: intersects && influence > 0.18,
  };
}

export function applyOrbFieldSampleToElement(
  el: HTMLElement,
  sample: OrbFieldSample | null,
): void {
  if (!sample) {
    el.style.removeProperty('--orb-push-x');
    el.style.removeProperty('--orb-push-y');
    el.style.removeProperty('--orb-scale');
    el.style.removeProperty('--orb-radius');
    el.style.removeProperty('--orb-local-x');
    el.style.removeProperty('--orb-local-y');
    el.style.removeProperty('--orb-bite-r');
    el.style.removeProperty('--orb-influence');
    el.dataset.orbInfluenced = '0';
    el.dataset.orbMask = '0';
    return;
  }

  el.style.setProperty('--orb-push-x', `${sample.pushX.toFixed(2)}px`);
  el.style.setProperty('--orb-push-y', `${sample.pushY.toFixed(2)}px`);
  el.style.setProperty('--orb-scale', sample.scale.toFixed(4));
  el.style.setProperty('--orb-radius', sample.radius);
  el.style.setProperty('--orb-local-x', `${sample.localX.toFixed(1)}px`);
  el.style.setProperty('--orb-local-y', `${sample.localY.toFixed(1)}px`);
  el.style.setProperty('--orb-bite-r', `${sample.biteR.toFixed(1)}px`);
  el.style.setProperty('--orb-influence', sample.influence.toFixed(3));
  el.dataset.orbInfluenced = '1';
  el.dataset.orbMask = sample.mask ? '1' : '0';
}
