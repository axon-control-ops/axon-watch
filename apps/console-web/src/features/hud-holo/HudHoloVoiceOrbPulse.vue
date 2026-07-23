<script setup lang="ts">
import { useLoop } from '@tresjs/core';
import type { BufferAttribute, BufferGeometry, Points } from 'three';

const props = defineProps<{
  points: Points;
  geometry: BufferGeometry;
  base: Float32Array;
  active?: boolean;
  listening?: boolean;
  speaking?: boolean;
}>();

const { onBeforeRender } = useLoop();
onBeforeRender(({ elapsed }) => {
  const attr = props.geometry.getAttribute('position') as BufferAttribute;
  const energy = props.speaking ? 1.35 : props.listening ? 1.2 : props.active ? 1.05 : 0.92;
  const wobble = props.listening || props.speaking ? 0.12 : 0.05;
  for (let i = 0; i < attr.count; i += 1) {
    const bx = props.base[i * 3];
    const by = props.base[i * 3 + 1];
    const bz = props.base[i * 3 + 2];
    const pulse = 1 + Math.sin(elapsed * 2.4 + i * 0.17) * wobble;
    attr.setXYZ(i, bx * energy * pulse, by * energy * pulse, bz * energy * pulse);
  }
  attr.needsUpdate = true;
  props.points.rotation.y = elapsed * (props.listening ? 0.55 : 0.22);
  props.points.rotation.x = Math.sin(elapsed * 0.6) * 0.15;
});
</script>

<template>
  <!-- animation driver only -->
  <TresGroup />
</template>
