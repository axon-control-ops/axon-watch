import {
  AdditiveBlending,
  Color,
  DoubleSide,
  Group,
  Mesh,
  MeshBasicMaterial,
  PlaneGeometry,
} from 'three';

type HoloPanelUserData = {
  coreEffect: 'holo-panel';
  spin: number;
  phase: number;
  baseOpacity: number;
};

/**
 * Thin holographic panes that orbit the VAXON core — JARVIS-style activity.
 */
export function buildVaxonCoreHolograms(radius: number): Group {
  const group = new Group();
  group.name = 'vaxon-core-holograms';
  const specs = [
    { w: 0.42, h: 0.26, dist: 1.55, spin: 0.011, phase: 0.2, tilt: 0.35 },
    { w: 0.34, h: 0.2, dist: 1.72, spin: -0.009, phase: 1.7, tilt: -0.55 },
    { w: 0.28, h: 0.18, dist: 1.9, spin: 0.014, phase: 3.1, tilt: 0.9 },
  ];
  for (const spec of specs) {
    const panel = new Mesh(
      new PlaneGeometry(radius * spec.w, radius * spec.h),
      new MeshBasicMaterial({
        color: new Color(0x7aebff),
        transparent: true,
        opacity: 0.22,
        depthWrite: false,
        blending: AdditiveBlending,
        side: DoubleSide,
      }),
    );
    panel.position.set(radius * spec.dist, radius * 0.15, 0);
    panel.rotation.y = Math.PI / 2;
    panel.rotation.z = spec.tilt;
    (panel.userData as HoloPanelUserData) = {
      coreEffect: 'holo-panel',
      spin: spec.spin,
      phase: spec.phase,
      baseOpacity: 0.22,
    };
    const pivot = new Group();
    pivot.rotation.y = spec.phase;
    pivot.add(panel);
    (pivot.userData as HoloPanelUserData) = {
      coreEffect: 'holo-panel',
      spin: spec.spin,
      phase: spec.phase,
      baseOpacity: 0.22,
    };
    group.add(pivot);
  }
  return group;
}

export function animateVaxonCoreHolograms(
  mesh: Mesh,
  clock: number,
  spinMul: number,
  opacityMul: number,
): void {
  mesh.traverse((child) => {
    const data = child.userData as Partial<HoloPanelUserData>;
    if (data.coreEffect !== 'holo-panel') {
      return;
    }
    if (child instanceof Group) {
      child.rotation.y += (data.spin ?? 0.01) * spinMul;
      child.rotation.x = Math.sin(clock * 0.9 + (data.phase ?? 0)) * 0.12;
      return;
    }
    if (child instanceof Mesh) {
      const material = child.material as MeshBasicMaterial;
      const wave = 0.65 + Math.sin(clock * 2.4 + (data.phase ?? 0)) * 0.35;
      material.opacity = (data.baseOpacity ?? 0.2) * wave * opacityMul;
      // Flicker open/close every few seconds.
      const gate = (Math.sin(clock * 0.55 + (data.phase ?? 0)) + 1) / 2;
      material.opacity *= 0.35 + gate * 0.65;
      child.visible = material.opacity > 0.05;
    }
  });
}
