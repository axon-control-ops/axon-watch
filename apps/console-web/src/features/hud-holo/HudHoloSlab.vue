<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue';
import { useLoop } from '@tresjs/core';
import {
  BoxGeometry,
  Color,
  EdgesGeometry,
  Euler,
  LineBasicMaterial,
  LineSegments,
  Vector3,
} from 'three';

import {
  HUD_HOLO_EDGE,
  HUD_HOLO_FILL,
  HUD_HOLO_FILL_OPACITY,
  type HudHoloTone,
} from './hud-holo-tones';

const props = withDefaults(
  defineProps<{
    tone?: HudHoloTone;
    parallaxX?: number;
    parallaxY?: number;
    reducedMotion?: boolean;
  }>(),
  {
    tone: 'nominal',
    parallaxX: 0,
    parallaxY: 0,
    reducedMotion: false,
  },
);

/** Keep the 3D backing subtly dimensional without misaligning readable DOM. */
const rotation = reactive(new Euler(0.025, -0.045, 0));
const fillPos = new Vector3(0, 0, -0.06);
const veilPos = new Vector3(0, 0, -0.1);
const scanPos = new Vector3(0, 0, 0.03);
const edgeOpacity = ref(0.92);
const fillOpacity = ref(HUD_HOLO_FILL_OPACITY.nominal);
const scanOpacity = ref(0.12);

const edgeColor = computed(() => HUD_HOLO_EDGE[props.tone]);
const fillColor = computed(() => HUD_HOLO_FILL[props.tone]);

/* EdgesGeometry draws only clean rectangle/corner edges. Plane wireframe
 * exposes triangulation diagonals, which read as broken lines through content. */
const frameBox = new BoxGeometry(4.35, 6.1, 0.08);
const frameGeometry = new EdgesGeometry(frameBox);
const frameMaterial = new LineBasicMaterial({
  color: new Color(HUD_HOLO_EDGE[props.tone]),
  transparent: true,
  opacity: 0.88,
});
const frame = new LineSegments(frameGeometry, frameMaterial);
frame.position.z = 0.02;

const innerBox = new BoxGeometry(4, 5.65, 0.04);
const innerGeometry = new EdgesGeometry(innerBox);
const innerMaterial = new LineBasicMaterial({
  color: new Color(0xb8ecff),
  transparent: true,
  opacity: 0.28,
});
const innerFrame = new LineSegments(innerGeometry, innerMaterial);
innerFrame.position.z = 0.05;

watch(edgeColor, (color) => frameMaterial.color.set(color));

const { onBeforeRender } = useLoop();

onBeforeRender(({ elapsed }) => {
  if (props.reducedMotion) {
    rotation.x = 0.025;
    rotation.y = -0.045;
    fillOpacity.value = HUD_HOLO_FILL_OPACITY[props.tone];
    frameMaterial.opacity = 0.82;
    return;
  }
  rotation.x = 0.025 + Math.cos(elapsed * 0.32) * 0.01 + props.parallaxY * 0.02;
  rotation.y = -0.045 + Math.sin(elapsed * 0.38) * 0.015 + props.parallaxX * 0.025;
  fillOpacity.value =
    HUD_HOLO_FILL_OPACITY[props.tone] + 0.025 + Math.sin(elapsed * 0.9) * 0.015;
  edgeOpacity.value = 0.72 + Math.sin(elapsed * 1.45) * 0.12;
  frameMaterial.opacity = edgeOpacity.value;
  innerMaterial.opacity = 0.2 + Math.sin(elapsed * 0.8) * 0.06;
  scanOpacity.value = 0.05 + Math.sin(elapsed * 2.2) * 0.035;
  scanPos.y = Math.sin(elapsed * 0.85) * 1.8;
});

onBeforeUnmount(() => {
  frameBox.dispose();
  frameGeometry.dispose();
  frameMaterial.dispose();
  innerBox.dispose();
  innerGeometry.dispose();
  innerMaterial.dispose();
});
</script>

<template>
  <TresGroup :rotation="rotation">
    <TresMesh :position="fillPos">
      <TresPlaneGeometry :args="[4.35, 6.1]" />
      <TresMeshBasicMaterial
        :color="fillColor"
        :transparent="true"
        :opacity="fillOpacity"
        :depth-write="false"
      />
    </TresMesh>

    <TresMesh :position="veilPos">
      <TresPlaneGeometry :args="[4.35, 6.1]" />
      <TresMeshBasicMaterial
        color="#040810"
        :transparent="true"
        :opacity="0.32"
        :depth-write="false"
      />
    </TresMesh>

    <!-- Scan band -->
    <TresMesh :position="scanPos">
      <TresPlaneGeometry :args="[4.2, 0.08]" />
      <TresMeshBasicMaterial
        :color="edgeColor"
        :transparent="true"
        :opacity="scanOpacity"
        :depth-write="false"
      />
    </TresMesh>

    <primitive :object="frame" />
    <primitive :object="innerFrame" />
  </TresGroup>
</template>
