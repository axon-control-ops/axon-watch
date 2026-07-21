/**
 * Temporary VAXON → workspace dispatch filament + employee mote.
 * Kept out of brain-galaxy-scene to stay under the file-size hard limit.
 */

import {
  AdditiveBlending,
  BufferGeometry,
  CatmullRomCurve3,
  Color,
  Group,
  Line,
  LineBasicMaterial,
  Mesh,
  MeshBasicMaterial,
  SphereGeometry,
  Vector3,
} from 'three';
import { CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';

export const SPECIALTY_DISPATCH_DURATION_MS = 2400;

export type SpecialtyDispatchFilament = {
  group: Group;
  startedAt: number;
  durationMs: number;
  curve: CatmullRomCurve3;
  bead: Mesh;
  mote: Mesh;
  lineMaterial: LineBasicMaterial;
  beadMaterial: MeshBasicMaterial;
  moteMaterial: MeshBasicMaterial;
  labelEl: HTMLElement | null;
};

export function formatSpecialtyRouteChip(notice: {
  toName: string;
  toRoleLabel: string;
  fromName?: string;
}): string {
  const to = notice.toName.trim() || 'teammate';
  const role = notice.toRoleLabel.trim();
  const from = notice.fromName?.trim();
  const head = role ? `→ ${to} · ${role}` : `→ ${to}`;
  return from ? `${head} · from ${from}` : head;
}

export function buildSpecialtyDispatchFilament(input: {
  from: Vector3;
  to: Vector3;
  label: string;
  nowMs?: number;
}): SpecialtyDispatchFilament {
  const from = input.from.clone();
  const to = input.to.clone();
  const mid = from.clone().lerp(to, 0.5);
  mid.y += 0.55;
  mid.x += (to.z - from.z) * 0.12;
  const curve = new CatmullRomCurve3([from, mid, to]);
  const points = curve.getPoints(28);
  const geometry = new BufferGeometry().setFromPoints(points);
  const lineMaterial = new LineBasicMaterial({
    color: new Color('#5ef0ff'),
    transparent: true,
    opacity: 0.95,
    depthWrite: false,
    blending: AdditiveBlending,
  });
  const line = new Line(geometry, lineMaterial);

  const beadMaterial = new MeshBasicMaterial({
    color: new Color('#9af8ff'),
    transparent: true,
    opacity: 1,
    depthWrite: false,
    blending: AdditiveBlending,
  });
  const bead = new Mesh(new SphereGeometry(0.055, 12, 12), beadMaterial);
  bead.position.copy(from);

  const moteMaterial = new MeshBasicMaterial({
    color: new Color('#7dffc8'),
    transparent: true,
    opacity: 0.95,
    depthWrite: false,
    blending: AdditiveBlending,
  });
  const mote = new Mesh(new SphereGeometry(0.09, 16, 16), moteMaterial);
  mote.position.copy(to);
  mote.position.y += 0.22;

  let labelEl: HTMLElement | null = null;
  if (typeof document !== 'undefined') {
    labelEl = document.createElement('span');
    labelEl.className = 'brain-galaxy-specialty-mote-label';
    labelEl.textContent = input.label;
    const labelObject = new CSS2DObject(labelEl);
    labelObject.position.set(0, 0.18, 0);
    mote.add(labelObject);
  }

  const group = new Group();
  group.name = 'specialty-dispatch-filament';
  group.add(line);
  group.add(bead);
  group.add(mote);

  return {
    group,
    startedAt: input.nowMs ?? performance.now(),
    durationMs: SPECIALTY_DISPATCH_DURATION_MS,
    curve,
    bead,
    mote,
    lineMaterial,
    beadMaterial,
    moteMaterial,
    labelEl,
  };
}

/** @returns false when the filament should be removed */
export function animateSpecialtyDispatchFilament(
  fx: SpecialtyDispatchFilament,
  nowMs: number,
): boolean {
  const elapsed = nowMs - fx.startedAt;
  const t = Math.min(1, Math.max(0, elapsed / fx.durationMs));
  const travel = Math.min(1, t / 0.72);
  fx.bead.position.copy(fx.curve.getPoint(travel));
  const fade = t < 0.75 ? 1 : 1 - (t - 0.75) / 0.25;
  fx.lineMaterial.opacity = 0.25 + 0.7 * fade;
  fx.beadMaterial.opacity = fade;
  fx.moteMaterial.opacity = 0.35 + 0.65 * fade;
  fx.mote.scale.setScalar(0.85 + Math.sin(nowMs * 0.012) * 0.08);
  if (fx.labelEl) {
    fx.labelEl.style.opacity = String(fade);
  }
  return t < 1;
}

export function disposeSpecialtyDispatchFilament(fx: SpecialtyDispatchFilament): void {
  fx.group.removeFromParent();
  fx.group.traverse((child) => {
    const mesh = child as Mesh;
    if (mesh.geometry) {
      mesh.geometry.dispose();
    }
    const material = (child as { material?: { dispose?: () => void } | Array<{ dispose?: () => void }> })
      .material;
    if (Array.isArray(material)) {
      material.forEach((entry) => entry.dispose?.());
    } else {
      material?.dispose?.();
    }
  });
}
