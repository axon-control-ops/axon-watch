<script setup lang="ts">
import { onBeforeUnmount } from 'vue';
import { useLoop } from '@tresjs/core';
import {
  AdditiveBlending,
  BufferAttribute,
  BufferGeometry,
  Color,
  DoubleSide,
  Mesh,
  MeshBasicMaterial,
  PlaneGeometry,
  Points,
  PointsMaterial,
} from 'three';

const props = withDefaults(
  defineProps<{
    reducedMotion?: boolean;
  }>(),
  { reducedMotion: false },
);

const dustCount = 420;
const dustPositions = new Float32Array(dustCount * 3);
for (let i = 0; i < dustCount; i += 1) {
  dustPositions[i * 3] = (Math.random() - 0.5) * 16;
  dustPositions[i * 3 + 1] = (Math.random() - 0.5) * 10;
  dustPositions[i * 3 + 2] = -2 - Math.random() * 8;
}
const dustGeo = new BufferGeometry();
dustGeo.setAttribute('position', new BufferAttribute(dustPositions, 3));
const dustMat = new PointsMaterial({
  color: new Color(0xb8ecff),
  size: 0.028,
  transparent: true,
  opacity: 0.7,
  depthWrite: false,
  blending: AdditiveBlending,
  sizeAttenuation: true,
});
const dust = new Points(dustGeo, dustMat);

const deskGeo = new PlaneGeometry(18, 10, 1, 1);
const deskMat = new MeshBasicMaterial({
  color: new Color(0x05080e),
  transparent: true,
  opacity: 0.78,
  side: DoubleSide,
  depthWrite: false,
});
const desk = new Mesh(deskGeo, deskMat);
desk.position.set(0, -2.6, -1.2);
desk.rotation.x = -Math.PI / 2.35;

const gridGeo = new PlaneGeometry(14, 8, 24, 14);
const gridMat = new MeshBasicMaterial({
  color: new Color(0x7aebff),
  transparent: true,
  opacity: 0.08,
  wireframe: true,
  depthWrite: false,
  side: DoubleSide,
});
const grid = new Mesh(gridGeo, gridMat);
grid.position.set(0, -2.35, -0.4);
grid.rotation.x = -Math.PI / 2.45;

const trayGeo = new PlaneGeometry(11, 3.4, 1, 1);
const trayMat = new MeshBasicMaterial({
  color: new Color(0x081018),
  transparent: true,
  opacity: 0.58,
  side: DoubleSide,
  depthWrite: false,
});
const tray = new Mesh(trayGeo, trayMat);
tray.position.set(0, -1.2, 1.15);
tray.rotation.x = -0.48;

const trayEdgeMat = new MeshBasicMaterial({
  color: new Color(0x7aebff),
  transparent: true,
  opacity: 0.38,
  wireframe: true,
  depthWrite: false,
});
const trayEdge = new Mesh(trayGeo.clone(), trayEdgeMat);
trayEdge.position.copy(tray.position);
trayEdge.position.z += 0.03;
trayEdge.rotation.copy(tray.rotation);

const { onBeforeRender } = useLoop();
onBeforeRender(({ elapsed }) => {
  if (props.reducedMotion) {
    return;
  }
  dust.rotation.y = elapsed * 0.018;
  const attr = dustGeo.getAttribute('position') as BufferAttribute;
  for (let i = 0; i < dustCount; i += 1) {
    let z = attr.getZ(i) + 0.008;
    if (z > 2) {
      z = -10;
    }
    attr.setZ(i, z);
  }
  attr.needsUpdate = true;
  gridMat.opacity = 0.055 + Math.sin(elapsed * 0.7) * 0.03;
  trayEdgeMat.opacity = 0.28 + Math.sin(elapsed * 1.1) * 0.1;
  tray.rotation.x = -0.48 + Math.sin(elapsed * 0.22) * 0.02;
  trayEdge.rotation.x = tray.rotation.x;
});

onBeforeUnmount(() => {
  dustGeo.dispose();
  dustMat.dispose();
  deskGeo.dispose();
  deskMat.dispose();
  gridGeo.dispose();
  gridMat.dispose();
  trayGeo.dispose();
  trayMat.dispose();
  trayEdge.geometry.dispose();
  trayEdgeMat.dispose();
});
</script>

<template>
  <primitive :object="dust" />
  <primitive :object="desk" />
  <primitive :object="grid" />
  <primitive :object="tray" />
  <primitive :object="trayEdge" />
</template>
