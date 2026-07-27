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
  feather: number;
  scale: number;
  radius: string;
  mask: boolean;
};

export const ORB_FIELD_MAX_PUSH = 64;
export const ORB_FIELD_SOFT_EXTRA = 72;
export const ORB_FIELD_DRAG_MAX_PUSH = 96;
export const ORB_FIELD_DRAG_SOFT_EXTRA = 100;

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export function orbVisualRadius(orb: Pick<OrbFieldBox, 'width' | 'height'>): number {
  return (Math.min(orb.width, orb.height) / 2) * 0.94;
}

export function orbCenter(orb: OrbFieldBox): { x: number; y: number } {
  return { x: orb.x + orb.width / 2, y: orb.y + orb.height / 2 };
}

export function sampleOrbFieldInfluence(options: {
  orb: OrbFieldBox;
  element: OrbFieldElementBox;
  maxPush?: number;
  softExtra?: number;
}): OrbFieldSample | null {
  const maxPush = options.maxPush ?? ORB_FIELD_MAX_PUSH;
  const softExtra = options.softExtra ?? ORB_FIELD_SOFT_EXTRA;
  const center = orbCenter(options.orb);
  const radius = orbVisualRadius(options.orb);
  const elCx = options.element.left + options.element.width / 2;
  const elCy = options.element.top + options.element.height / 2;
  const dx = elCx - center.x;
  const dy = elCy - center.y;
  const dist = Math.hypot(dx, dy);
  const elementReach = Math.min(options.element.width, options.element.height) * 0.5;
  const clearance = radius + softExtra + elementReach;

  if (dist > clearance || clearance <= 0) {
    return null;
  }

  const overlap = clearance - dist;
  const raw = clamp(overlap / clearance, 0, 1);
  const influence = clamp(raw * raw * 0.4 + raw * 0.6, 0, 1);
  if (influence < 0.03) {
    return null;
  }

  const nx = dist > 0.001 ? dx / dist : 0;
  const ny = dist > 0.001 ? dy / dist : -1;
  const pushX = nx * maxPush * influence;
  const pushY = ny * maxPush * influence;
  const localX = center.x - options.element.left;
  const localY = center.y - options.element.top;
  const biteR = radius + 18 + influence * 34;
  const feather = 10 + influence * 20;
  const intersects =
    localX > -biteR &&
    localX < options.element.width + biteR &&
    localY > -biteR &&
    localY < options.element.height + biteR;

  const round = 0.5 + influence * 1.7;
  const radiusCss = `${(0.45 + influence * 0.8).toFixed(2)}rem ${round.toFixed(2)}rem ${(0.55 + influence * 1).toFixed(2)}rem ${(0.45 + influence * 0.6).toFixed(2)}rem / ${(0.55 + influence * 1.2).toFixed(2)}rem ${(0.45 + influence * 0.7).toFixed(2)}rem ${(0.6 + influence * 1.15).toFixed(2)}rem ${(0.45 + influence * 0.55).toFixed(2)}rem`;

  return {
    pushX,
    pushY,
    influence,
    localX,
    localY,
    biteR,
    feather,
    scale: 1 - influence * 0.08,
    radius: radiusCss,
    mask: intersects && influence > 0.08,
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
    el.style.removeProperty('--orb-feather');
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
  el.style.setProperty('--orb-feather', `${sample.feather.toFixed(1)}px`);
  el.style.setProperty('--orb-influence', sample.influence.toFixed(3));
  el.dataset.orbInfluenced = '1';
  el.dataset.orbMask = sample.mask ? '1' : '0';
}
