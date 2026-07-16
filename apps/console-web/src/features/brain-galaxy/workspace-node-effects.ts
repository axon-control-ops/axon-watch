import {
  AdditiveBlending,
  Color,
  DoubleSide,
  Mesh,
  MeshStandardMaterial,
  PointLight,
  SphereGeometry,
  TorusGeometry,
} from 'three';

import type { GalaxyNodeColors } from './brain-galaxy-colors';

type WorkspaceEffectData = {
  workspaceEffect: 'halo' | 'ring' | 'light';
  baseOpacity?: number;
  baseIntensity?: number;
  phase: number;
  spin?: number;
};

export function decorateWorkspaceNode(
  mesh: Mesh,
  radius: number,
  colors: GalaxyNodeColors,
  phase: number,
): void {
  const material = mesh.material as MeshStandardMaterial;
  material.emissive = new Color(colors.base);
  material.emissiveIntensity = Math.max(colors.emissiveIntensity, 0.8);
  material.metalness = 0.22;
  material.roughness = 0.3;

  const halo = new Mesh(
    new SphereGeometry(radius * 1.42, 24, 24),
    new MeshStandardMaterial({
      color: colors.base,
      emissive: new Color(colors.base),
      emissiveIntensity: 1.25,
      transparent: true,
      opacity: 0.14,
      depthWrite: false,
      side: DoubleSide,
      blending: AdditiveBlending,
    }),
  );
  (halo.userData as WorkspaceEffectData) = {
    workspaceEffect: 'halo',
    baseOpacity: 0.14,
    phase,
  };
  mesh.add(halo);

  const ring = new Mesh(
    new TorusGeometry(radius * 1.34, 0.012, 10, 48),
    new MeshStandardMaterial({
      color: 0xa9f4ff,
      emissive: new Color(colors.base),
      emissiveIntensity: 1.4,
      transparent: true,
      opacity: 0.62,
      depthWrite: false,
      side: DoubleSide,
      blending: AdditiveBlending,
    }),
  );
  ring.rotation.x = Math.PI / 2 + Math.sin(phase) * 0.5;
  (ring.userData as WorkspaceEffectData) = {
    workspaceEffect: 'ring',
    baseOpacity: 0.62,
    phase,
    spin: 0.004 + (phase % 0.006),
  };
  mesh.add(ring);

  const light = new PointLight(colors.base, 0.7, radius * 7, 2);
  (light.userData as WorkspaceEffectData) = {
    workspaceEffect: 'light',
    baseIntensity: 0.7,
    phase,
  };
  mesh.add(light);
}

export function animateWorkspaceNode(
  mesh: Mesh,
  clock: number,
  presenceAmp: number,
  selected: boolean,
  focusStrength = 1,
): void {
  const amp = Math.max(0, Math.min(1, presenceAmp));
  const phase = mesh.position.x * 1.7 + mesh.position.z * 1.3;
  const wave = Math.sin(clock * (1.35 + amp * 2.05) + phase);
  const scale = 1 + wave * (0.025 + amp * 0.04) + (selected ? 0.06 : 0);
  mesh.scale.setScalar(scale);

  const material = mesh.material as MeshStandardMaterial;
  material.emissiveIntensity =
    ((selected ? 1.65 : 0.88 + amp * 0.32) + wave * 0.18) * focusStrength;
  material.opacity = focusStrength;
  material.transparent = focusStrength < 1;

  mesh.traverse((child) => {
    const data = child.userData as Partial<WorkspaceEffectData>;
    if (!data.workspaceEffect) {
      return;
    }
    const effectWave =
      0.82 + Math.sin(clock * (1.7 + amp * 2.5) + (data.phase ?? 0)) * 0.18;
    if (data.workspaceEffect === 'halo' && child instanceof Mesh) {
      const haloMaterial = child.material as MeshStandardMaterial;
      haloMaterial.opacity =
        (data.baseOpacity ?? 0.14) *
        effectWave *
        (1 + amp * 0.8) *
        (selected ? 1.35 : 1) *
        focusStrength;
    } else if (data.workspaceEffect === 'ring' && child instanceof Mesh) {
      child.rotation.z += (data.spin ?? 0.006) * (1 + amp * 2.2);
      const ringMaterial = child.material as MeshStandardMaterial;
      ringMaterial.opacity =
        (data.baseOpacity ?? 0.62) * effectWave * (selected ? 1.2 : 1) * focusStrength;
    } else if (data.workspaceEffect === 'light' && child instanceof PointLight) {
      child.intensity =
        (data.baseIntensity ?? 0.7) *
        effectWave *
        (1 + amp * 0.9) *
        (selected ? 1.4 : 1) *
        focusStrength;
    }
  });
}
