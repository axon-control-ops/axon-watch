import {
  AdditiveBlending,
  Color,
  DoubleSide,
  Group,
  Mesh,
  MeshStandardMaterial,
  PointLight,
  SphereGeometry,
  TorusGeometry,
} from 'three';

import type { GalaxyNodeColors } from './brain-galaxy-colors';
import type { GalaxyCoreOrbMode } from './galaxy-presence-state';

export const VAXON_CORE_ORB_RADIUS = 0.78;

type CoreMotionProfile = {
  waveFreq: number;
  spinMul: number;
  opacityMul: number;
  scaleSwing: number;
  lightMul: number;
  orbitMul: number;
  pulseFreq: number;
  pulseAmp: number;
  yawSpeed: number;
  emissiveBase: number;
  emissiveSwing: number;
  tint: number | null;
};

const CORE_MOTION: Record<GalaxyCoreOrbMode, CoreMotionProfile> = {
  idle: {
    waveFreq: 1.8,
    spinMul: 1,
    opacityMul: 1,
    scaleSwing: 0.08,
    lightMul: 1,
    orbitMul: 1,
    pulseFreq: 2.2,
    pulseAmp: 0.045,
    yawSpeed: 0.002,
    emissiveBase: 1.55,
    emissiveSwing: 0.38,
    tint: null,
  },
  listening: {
    waveFreq: 3.4,
    spinMul: 2.2,
    opacityMul: 1.2,
    scaleSwing: 0.12,
    lightMul: 1.45,
    orbitMul: 2.4,
    pulseFreq: 3.6,
    pulseAmp: 0.065,
    yawSpeed: 0.004,
    emissiveBase: 2.05,
    emissiveSwing: 0.55,
    tint: 0x5cffb4,
  },
  busy: {
    waveFreq: 4.8,
    spinMul: 4.2,
    opacityMul: 1.35,
    scaleSwing: 0.15,
    lightMul: 1.9,
    orbitMul: 5.5,
    pulseFreq: 4.2,
    pulseAmp: 0.085,
    yawSpeed: 0.008,
    emissiveBase: 2.35,
    emissiveSwing: 0.8,
    tint: 0x48c4ff,
  },
  speaking: {
    waveFreq: 5.4,
    spinMul: 3.6,
    opacityMul: 1.45,
    scaleSwing: 0.18,
    lightMul: 2.15,
    orbitMul: 4.8,
    pulseFreq: 5.6,
    pulseAmp: 0.1,
    yawSpeed: 0.01,
    emissiveBase: 2.55,
    emissiveSwing: 0.95,
    tint: 0x9ef0ff,
  },
  autonomous: {
    waveFreq: 3.8,
    spinMul: 3.2,
    opacityMul: 1.4,
    scaleSwing: 0.14,
    lightMul: 1.85,
    orbitMul: 4.2,
    pulseFreq: 3.2,
    pulseAmp: 0.075,
    yawSpeed: 0.007,
    emissiveBase: 2.2,
    emissiveSwing: 0.7,
    tint: 0xffb347,
  },
  alerting: {
    waveFreq: 6.2,
    spinMul: 5.2,
    opacityMul: 1.55,
    scaleSwing: 0.2,
    lightMul: 2.4,
    orbitMul: 6.2,
    pulseFreq: 6.8,
    pulseAmp: 0.11,
    yawSpeed: 0.012,
    emissiveBase: 2.7,
    emissiveSwing: 1.1,
    tint: 0xff6b6b,
  },
};

type CoreRingUserData = {
  coreEffect: 'ring' | 'inner' | 'mid-halo' | 'outer-halo' | 'light' | 'orbit';
  spin?: number;
  baseOpacity?: number;
  baseIntensity?: number;
  phase?: number;
};

/**
 * Mockup "VAXON Core" orb as a volumetric 3D sphere:
 * bright plasma core + glass shell + concentric glow rings.
 */
export function decorateVaxonCoreOrb(
  mesh: Mesh,
  radius: number,
  colors: GalaxyNodeColors,
): void {
  mesh.geometry.dispose();
  mesh.geometry = new SphereGeometry(radius, 48, 48);
  const shell = mesh.material as MeshStandardMaterial;
  shell.color = new Color(0x7aebff);
  shell.emissive = new Color(colors.emissive || 0x28b8ff);
  shell.emissiveIntensity = Math.max(colors.emissiveIntensity, 2.1);
  shell.metalness = 0.12;
  shell.roughness = 0.16;
  shell.transparent = true;
  shell.opacity = 0.94;

  const inner = new Mesh(
    new SphereGeometry(radius * 0.55, 32, 32),
    new MeshStandardMaterial({
      color: 0xe8fbff,
      emissive: new Color(0x48c4ff),
      emissiveIntensity: 3.2,
      metalness: 0.05,
      roughness: 0.14,
    }),
  );
  (inner.userData as CoreRingUserData) = { coreEffect: 'inner', phase: 0 };
  mesh.add(inner);

  const midHalo = new Mesh(
    new SphereGeometry(radius * 1.28, 32, 32),
    new MeshStandardMaterial({
      color: 0x48c4ff,
      emissive: new Color(0x48c4ff),
      emissiveIntensity: 0.9,
      transparent: true,
      opacity: 0.14,
      depthWrite: false,
      side: DoubleSide,
    }),
  );
  (midHalo.userData as CoreRingUserData) = {
    coreEffect: 'mid-halo',
    baseOpacity: 0.14,
    phase: 0.8,
  };
  mesh.add(midHalo);

  const outerHalo = new Mesh(
    new SphereGeometry(radius * 1.62, 28, 28),
    new MeshStandardMaterial({
      color: 0x1ad4ff,
      emissive: new Color(0x1ad4ff),
      emissiveIntensity: 0.55,
      transparent: true,
      opacity: 0.08,
      depthWrite: false,
      side: DoubleSide,
    }),
  );
  (outerHalo.userData as CoreRingUserData) = {
    coreEffect: 'outer-halo',
    baseOpacity: 0.08,
    phase: 2.2,
  };
  mesh.add(outerHalo);

  const rings = new Group();
  rings.add(buildCoreRing(radius * 1.18, 0.018, 0.012, 0.35));
  rings.add(buildCoreRing(radius * 1.42, 0.014, -0.009, -0.55));
  rings.add(buildCoreRing(radius * 1.68, 0.01, 0.007, 0.85));
  rings.add(buildCoreRing(radius * 0.82, 0.009, -0.016, 0.05));
  // Tilted equatorial JARVIS ring for cinematic depth.
  const tilted = buildCoreRing(radius * 1.32, 0.02, 0.015, 1.1);
  tilted.rotation.x = Math.PI / 2.6;
  rings.add(tilted);
  mesh.add(rings);

  mesh.add(buildEnergyOrbit(radius));

  const light = new PointLight(0x48c4ff, 2.4, radius * 8, 2);
  light.position.set(0, 0, 0);
  (light.userData as CoreRingUserData) = {
    coreEffect: 'light',
    baseIntensity: 2.4,
    phase: 0,
  };
  mesh.add(light);
}

function buildCoreRing(
  ringRadius: number,
  tube: number,
  spin: number,
  tilt: number,
): Mesh {
  const ring = new Mesh(
    new TorusGeometry(ringRadius, tube, 12, 72),
    new MeshStandardMaterial({
      color: 0x9ef0ff,
      emissive: new Color(0x48c4ff),
      emissiveIntensity: 1.4,
      transparent: true,
      opacity: 0.55,
      depthWrite: false,
      blending: AdditiveBlending,
      side: DoubleSide,
    }),
  );
  ring.rotation.x = Math.PI / 2 + tilt;
  (ring.userData as CoreRingUserData) = {
    coreEffect: 'ring',
    spin,
    baseOpacity: 0.55,
    phase: tilt,
  };
  return ring;
}

function buildEnergyOrbit(radius: number): Group {
  const orbit = new Group();
  (orbit.userData as CoreRingUserData) = {
    coreEffect: 'orbit',
    spin: 0.006,
    phase: 1.1,
  };
  orbit.rotation.x = 0.7;
  orbit.rotation.z = -0.45;

  for (let index = 0; index < 12; index += 1) {
    const angle = (index / 12) * Math.PI * 2;
    const bead = new Mesh(
      new SphereGeometry(radius * (index % 3 === 0 ? 0.045 : 0.026), 12, 12),
      new MeshStandardMaterial({
        color: index % 3 === 0 ? 0xffffff : 0x7aebff,
        emissive: new Color(0x48c4ff),
        emissiveIntensity: index % 3 === 0 ? 2.8 : 1.9,
        transparent: true,
        opacity: 0.9,
        depthWrite: false,
        blending: AdditiveBlending,
      }),
    );
    bead.position.set(Math.cos(angle) * radius * 1.9, Math.sin(angle) * radius * 1.9, 0);
    orbit.add(bead);
  }
  return orbit;
}

export function animateVaxonCoreOrb(
  mesh: Mesh,
  clock: number,
  modeOrBusy: GalaxyCoreOrbMode | boolean,
  selected = false,
  voiceEnergy = 0,
): void {
  const mode: GalaxyCoreOrbMode =
    typeof modeOrBusy === 'boolean' ? (modeOrBusy ? 'busy' : 'idle') : modeOrBusy;
  const profile = CORE_MOTION[mode];
  const busyLike = mode !== 'idle';
  const energy = Math.max(0, Math.min(1.4, voiceEnergy));

  mesh.traverse((child) => {
    const data = child.userData as Partial<CoreRingUserData>;
    if (!data.coreEffect) {
      return;
    }
    const wave = 0.78 + Math.sin(clock * profile.waveFreq + (data.phase ?? 0)) * 0.22;
    if (data.coreEffect === 'ring' && child instanceof Mesh) {
      const speed = (data.spin ?? 0.01) * profile.spinMul * (1 + energy * 0.35);
      child.rotation.z += speed;
      child.rotation.y += speed * 0.28;
      const ringMaterial = child.material as MeshStandardMaterial;
      ringMaterial.opacity =
        (data.baseOpacity ?? 0.55) * wave * profile.opacityMul * (1 + energy * 0.2);
      if (profile.tint) {
        ringMaterial.emissive = new Color(profile.tint);
      }
    } else if (data.coreEffect === 'inner' && child instanceof Mesh) {
      child.scale.setScalar(0.94 + wave * profile.scaleSwing + energy * 0.04);
      const innerMaterial = child.material as MeshStandardMaterial;
      innerMaterial.emissiveIntensity = (busyLike ? 3.8 : 2.5) + wave * 0.6 + energy * 0.9;
      if (profile.tint) {
        innerMaterial.emissive = new Color(profile.tint);
      }
    } else if (
      (data.coreEffect === 'mid-halo' || data.coreEffect === 'outer-halo') &&
      child instanceof Mesh
    ) {
      const haloMaterial = child.material as MeshStandardMaterial;
      haloMaterial.opacity =
        (data.baseOpacity ?? 0.1) *
        wave *
        (busyLike ? 2.15 : 1) *
        (selected ? 1.25 : 1) *
        (mode === 'alerting' ? 1.35 : 1) *
        (1 + energy * 0.35);
      child.scale.setScalar(0.97 + wave * (busyLike ? 0.08 : 0.035) + energy * 0.03);
    } else if (data.coreEffect === 'light' && child instanceof PointLight) {
      child.intensity =
        (data.baseIntensity ?? 2.4) *
        (0.85 + wave * 0.3) *
        profile.lightMul *
        (1 + energy * 0.55);
      if (profile.tint) {
        child.color = new Color(profile.tint);
      }
    } else if (data.coreEffect === 'orbit' && child instanceof Group) {
      child.rotation.z += (data.spin ?? 0.006) * profile.orbitMul * (1 + energy * 0.4);
      child.rotation.y += (data.spin ?? 0.006) * (busyLike ? 2.5 : 0.45);
    }
  });

  const pulse =
    1 +
    Math.sin(clock * profile.pulseFreq) * (profile.pulseAmp + energy * 0.04) +
    energy * 0.06 +
    (selected ? 0.04 : 0);
  mesh.scale.setScalar(pulse);
  mesh.rotation.y += profile.yawSpeed * (1 + energy * 0.25);

  const material = mesh.material as MeshStandardMaterial;
  const base = selected && mode === 'idle' ? 1.85 : profile.emissiveBase;
  material.emissiveIntensity =
    base +
    Math.sin(clock * profile.pulseFreq) * profile.emissiveSwing +
    energy * 0.75;
  if (profile.tint) {
    material.emissive = new Color(profile.tint);
  }
}
