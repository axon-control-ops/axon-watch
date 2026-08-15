<script setup lang="ts">
/**
 * Spherical particle cloud for VAXON voice — concept-art mic orb.
 */
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { TresCanvas } from '@tresjs/core';
import { BloomPmndrs, EffectComposerPmndrs } from '@tresjs/post-processing';
import {
  AdditiveBlending,
  BufferAttribute,
  BufferGeometry,
  Color,
  Points,
  PointsMaterial,
  Vector3,
} from 'three';

import { probeWebGlAvailability } from '../brain-galaxy/webgl-availability';
import HudHoloVoiceOrbPulse from './HudHoloVoiceOrbPulse.vue';

const props = withDefaults(
  defineProps<{
    active?: boolean;
    listening?: boolean;
    speaking?: boolean;
  }>(),
  {
    active: false,
    listening: false,
    speaking: false,
  },
);

const webglOk = ref(false);
const cameraPosition = new Vector3(0, 0, 3.2);
const count = 320;
const positions = new Float32Array(count * 3);
const base = new Float32Array(count * 3);
for (let i = 0; i < count; i += 1) {
  const u = Math.random();
  const v = Math.random();
  const theta = 2 * Math.PI * u;
  const phi = Math.acos(2 * v - 1);
  const r = 0.72 + Math.random() * 0.35;
  const x = r * Math.sin(phi) * Math.cos(theta);
  const y = r * Math.sin(phi) * Math.sin(theta);
  const z = r * Math.cos(phi);
  positions[i * 3] = x;
  positions[i * 3 + 1] = y;
  positions[i * 3 + 2] = z;
  base[i * 3] = x;
  base[i * 3 + 1] = y;
  base[i * 3 + 2] = z;
}
const geometry = new BufferGeometry();
geometry.setAttribute('position', new BufferAttribute(positions, 3));
const material = new PointsMaterial({
  color: new Color(0x7aebff),
  size: 0.045,
  transparent: true,
  opacity: 0.85,
  depthWrite: false,
  blending: AdditiveBlending,
  sizeAttenuation: true,
});
const points = new Points(geometry, material);

watch(
  () => [props.speaking, props.listening] as const,
  ([speaking, listening]) => {
    if (speaking) {
      material.color.set('#ff6aa8');
    } else if (listening) {
      material.color.set('#ffa040');
    } else {
      material.color.set('#7aebff');
    }
  },
  { immediate: true },
);

onMounted(() => {
  webglOk.value = probeWebGlAvailability().ok;
});

onBeforeUnmount(() => {
  geometry.dispose();
  material.dispose();
});
</script>

<template>
  <div
    v-if="webglOk"
    class="hud-holo-voice-orb"
    aria-hidden="true"
    :data-listening="listening ? '1' : '0'"
    :data-speaking="speaking ? '1' : '0'"
  >
    <TresCanvas
      class="hud-holo-voice-orb__canvas"
      :alpha="true"
      :clear-color="'#000000'"
      :window-size="false"
      render-mode="always"
    >
      <TresPerspectiveCamera :position="cameraPosition" :fov="40" />
      <TresAmbientLight :intensity="0.5" />
      <primitive :object="points" />
      <HudHoloVoiceOrbPulse
        :points="points"
        :geometry="geometry"
        :base="base"
        :active="active"
        :listening="listening"
        :speaking="speaking"
      />
      <EffectComposerPmndrs>
        <BloomPmndrs
          :intensity="listening || speaking ? 1.8 : 1.1"
          :luminance-threshold="0.12"
          :luminance-smoothing="0.35"
          :mipmap-blur="true"
        />
      </EffectComposerPmndrs>
    </TresCanvas>
  </div>
</template>
