<script setup lang="ts">
import { onBeforeUnmount } from 'vue';
import { useLoop } from '@tresjs/core';
import {
  AdditiveBlending,
  BufferAttribute,
  BufferGeometry,
  Points,
  PointsMaterial,
} from 'three';

const props = withDefaults(
  defineProps<{
    reducedMotion?: boolean;
  }>(),
  { reducedMotion: false },
);

const count = 56;
const positions = new Float32Array(count * 3);
for (let i = 0; i < count; i += 1) {
  positions[i * 3] = (Math.random() - 0.5) * 4.2;
  positions[i * 3 + 1] = (Math.random() - 0.5) * 5.9;
  positions[i * 3 + 2] = (Math.random() - 0.5) * 0.5 - 0.05;
}

const geometry = new BufferGeometry();
geometry.setAttribute('position', new BufferAttribute(positions, 3));

const material = new PointsMaterial({
  color: 0xb8ecff,
  size: 0.035,
  transparent: true,
  opacity: 0.55,
  depthWrite: false,
  sizeAttenuation: true,
  blending: AdditiveBlending,
});

const points = new Points(geometry, material);

const { onBeforeRender } = useLoop();
onBeforeRender(({ elapsed }) => {
  if (props.reducedMotion) {
    return;
  }
  points.rotation.z = elapsed * 0.045;
  const attr = geometry.getAttribute('position') as BufferAttribute;
  for (let i = 0; i < count; i += 1) {
    const z = attr.getZ(i) + 0.0012;
    attr.setZ(i, z > 0.28 ? -0.28 : z);
  }
  attr.needsUpdate = true;
});

onBeforeUnmount(() => {
  geometry.dispose();
  material.dispose();
});
</script>

<template>
  <primitive :object="points" />
</template>
