import {
  ACESFilmicToneMapping,
  AdditiveBlending,
  AmbientLight,
  BufferAttribute,
  BufferGeometry,
  Color,
  Group,
  HemisphereLight,
  PointLight,
  Points,
  PointsMaterial,
  Scene,
  SRGBColorSpace,
  WebGLRenderer,
} from 'three';

type StarLayerData = {
  starLayer: true;
  baseOpacity: number;
  phase: number;
  speed: number;
  rotationSpeed: number;
};

type LiveLightData = {
  liveLight: true;
  baseIntensity: number;
  phase: number;
};

function seededRandom(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state * 1664525 + 1013904223) >>> 0;
    return state / 0x100000000;
  };
}

export function configureGalaxyRenderer(renderer: WebGLRenderer): void {
  renderer.outputColorSpace = SRGBColorSpace;
  renderer.toneMapping = ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.35;
}

export function buildGalaxyLighting(): Group {
  const lights = new Group();
  lights.name = 'galaxy-light-rig';
  lights.add(new AmbientLight(0x1b4262, 1.15));
  lights.add(new HemisphereLight(0x6adfff, 0x02060b, 1.3));
  lights.add(buildLiveLight(0x66e8ff, 4.8, 24, 3.5, 4.5, 5, 0));
  lights.add(buildLiveLight(0x167dff, 3.4, 20, -4.5, 1.2, 2.5, 1.8));
  lights.add(buildLiveLight(0x35ffd0, 2.6, 18, 0, -3.2, -4, 3.4));
  lights.add(buildLiveLight(0xff8a45, 0.85, 14, -2.5, -1.4, -2, 4.7));
  return lights;
}

function buildLiveLight(
  color: number,
  intensity: number,
  distance: number,
  x: number,
  y: number,
  z: number,
  phase: number,
): PointLight {
  const light = new PointLight(color, intensity, distance, 1.7);
  light.position.set(x, y, z);
  (light.userData as LiveLightData) = {
    liveLight: true,
    baseIntensity: intensity,
    phase,
  };
  return light;
}

export function buildAnimatedStarfield(): Group {
  const field = new Group();
  field.name = 'animated-starfield';
  field.add(buildStarLayer(1450, 6, 24, 0x78cfff, 0.032, 0.7, 11));
  field.add(buildStarLayer(760, 5, 18, 0xc8f6ff, 0.052, 0.78, 29));
  field.add(buildStarLayer(260, 4, 13, 0x42f2ff, 0.085, 0.86, 47));
  field.add(buildStarLayer(90, 3.5, 10, 0xffffff, 0.12, 0.72, 83));
  return field;
}

function buildStarLayer(
  count: number,
  minRadius: number,
  maxRadius: number,
  color: number,
  size: number,
  opacity: number,
  seed: number,
): Points {
  const random = seededRandom(seed);
  const positions = new Float32Array(count * 3);
  for (let index = 0; index < count; index += 1) {
    const radius = minRadius + random() * (maxRadius - minRadius);
    const theta = random() * Math.PI * 2;
    const phi = Math.acos(2 * random() - 1);
    positions[index * 3] = radius * Math.sin(phi) * Math.cos(theta);
    positions[index * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
    positions[index * 3 + 2] = radius * Math.cos(phi);
  }
  const geometry = new BufferGeometry();
  geometry.setAttribute('position', new BufferAttribute(positions, 3));
  const material = new PointsMaterial({
    color: new Color(color),
    size,
    transparent: true,
    opacity,
    sizeAttenuation: true,
    depthWrite: false,
    blending: AdditiveBlending,
  });
  const layer = new Points(geometry, material);
  (layer.userData as StarLayerData) = {
    starLayer: true,
    baseOpacity: opacity,
    phase: random() * Math.PI * 2,
    speed: 0.45 + random() * 0.75,
    rotationSpeed: (0.00008 + random() * 0.00016) * (random() > 0.5 ? 1 : -1),
  };
  return layer;
}

export function animateGalaxyAmbience(
  scene: Scene,
  starfield: Group | null,
  clock: number,
  busy: boolean,
): void {
  if (starfield) {
    starfield.children.forEach((child) => {
      if (!(child instanceof Points)) {
        return;
      }
      const data = child.userData as Partial<StarLayerData>;
      if (!data.starLayer) {
        return;
      }
      const material = child.material as PointsMaterial;
      const twinkle = 0.78 + Math.sin(clock * (data.speed ?? 1) + (data.phase ?? 0)) * 0.22;
      material.opacity = (data.baseOpacity ?? 0.7) * twinkle * (busy ? 1.22 : 1);
      child.rotation.y += (data.rotationSpeed ?? 0.0001) * (busy ? 2.4 : 1);
      child.rotation.x += (data.rotationSpeed ?? 0.0001) * 0.18;
    });
  }

  scene.traverse((object) => {
    if (!(object instanceof PointLight)) {
      return;
    }
    const data = object.userData as Partial<LiveLightData>;
    if (!data.liveLight) {
      return;
    }
    const shimmer = 0.92 + Math.sin(clock * (busy ? 2.8 : 0.9) + (data.phase ?? 0)) * 0.08;
    object.intensity = (data.baseIntensity ?? 1) * shimmer * (busy ? 1.35 : 1);
  });
}
