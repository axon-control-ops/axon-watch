<script setup lang="ts">
import { onBeforeUnmount, watch } from 'vue';
import { useLoop } from '@tresjs/core';
import {
  AdditiveBlending,
  Color,
  Group,
  Mesh,
  MeshBasicMaterial,
  PlaneGeometry,
} from 'three';

import {
  HUD_HOLO_EDGE,
  type HudHoloSignal,
  type HudHoloTone,
} from './hud-holo-tones';

const props = withDefaults(
  defineProps<{
    signals?: HudHoloSignal[];
    reducedMotion?: boolean;
    /** World-space width of the lattice region. */
    width?: number;
    /** World-space height of the lattice region. */
    height?: number;
    /** Vertical offset (negative = lower in slab). */
    offsetY?: number;
  }>(),
  {
    signals: () => [],
    reducedMotion: false,
    width: 3.6,
    height: 2.4,
    offsetY: -0.55,
  },
);

const root = new Group();
root.position.z = -0.04;

const padGeometry = new PlaneGeometry(0.52, 0.36);
const pads: Array<{
  mesh: Mesh;
  material: MeshBasicMaterial;
  tone: HudHoloTone;
  selected: boolean;
  weight: number;
  phase: number;
}> = [];

function clearPads(): void {
  for (const pad of pads) {
    root.remove(pad.mesh);
    pad.material.dispose();
  }
  pads.length = 0;
}

function rebuild(): void {
  clearPads();
  const signals = props.signals ?? [];
  if (!signals.length) {
    return;
  }

  const cols = Math.min(4, Math.max(2, Math.ceil(Math.sqrt(signals.length))));
  const rows = Math.ceil(signals.length / cols);
  const cellW = props.width / cols;
  const cellH = props.height / Math.max(rows, 1);
  const originX = -props.width / 2 + cellW / 2;
  const originY = props.offsetY + props.height / 2 - cellH / 2;

  signals.forEach((signal, index) => {
    const col = index % cols;
    const row = Math.floor(index / cols);
    const material = new MeshBasicMaterial({
      color: new Color(HUD_HOLO_EDGE[signal.tone]),
      transparent: true,
      opacity: signal.selected ? 0.42 : 0.18,
      depthWrite: false,
      blending: AdditiveBlending,
    });
    const mesh = new Mesh(padGeometry, material);
    mesh.position.set(originX + col * cellW, originY - row * cellH, 0);
    if (signal.selected) {
      mesh.scale.set(1.18, 1.18, 1);
    }
    root.add(mesh);
    pads.push({
      mesh,
      material,
      tone: signal.tone,
      selected: Boolean(signal.selected),
      weight: Math.max(0.15, Math.min(1, signal.weight ?? 1)),
      phase: index * 0.37,
    });
  });
}

watch(
  () => props.signals,
  () => rebuild(),
  { deep: true, immediate: true },
);

const { onBeforeRender } = useLoop();
onBeforeRender(({ elapsed }) => {
  if (props.reducedMotion) {
    for (const pad of pads) {
      pad.material.opacity = (pad.selected ? 0.36 : 0.16) * pad.weight;
    }
    return;
  }
  for (const pad of pads) {
    const pulse = 0.5 + 0.5 * Math.sin(elapsed * (pad.selected ? 2.4 : 1.35) + pad.phase);
    const base = pad.selected ? 0.28 : 0.12;
    pad.material.opacity = (base + pulse * (pad.selected ? 0.28 : 0.14)) * pad.weight;
  }
});

onBeforeUnmount(() => {
  clearPads();
  padGeometry.dispose();
});
</script>

<template>
  <primitive :object="root" />
</template>
