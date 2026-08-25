<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { TresCanvas } from '@tresjs/core';
import { BloomPmndrs, EffectComposerPmndrs, VignettePmndrs } from '@tresjs/post-processing';
import { Vector3 } from 'three';

import { probeWebGlAvailability } from '../brain-galaxy/webgl-availability';
import HudHoloAtmosphereField from './HudHoloAtmosphereField.vue';

const webglOk = ref(false);
const reducedMotion = ref(false);
const cameraPosition = new Vector3(0, 0.35, 7.2);
const lightA = new Vector3(2.5, 1.8, 3);
const lightB = new Vector3(-3, -0.5, 2);
const lightC = new Vector3(0, -2, 1.5);

onMounted(() => {
  reducedMotion.value = Boolean(
    typeof window !== 'undefined' &&
      window.matchMedia?.('(prefers-reduced-motion: reduce)').matches,
  );
  const probe = probeWebGlAvailability();
  webglOk.value = probe.ok;
});
</script>

<template>
  <div
    v-if="webglOk"
    class="hud-holo-atmosphere"
    aria-hidden="true"
    data-holo-atmosphere="1"
  >
    <TresCanvas
      class="hud-holo-atmosphere__canvas"
      :alpha="true"
      :clear-color="'#000000'"
      :window-size="false"
      render-mode="always"
    >
      <TresPerspectiveCamera :position="cameraPosition" :fov="42" />
      <TresAmbientLight :intensity="0.42" />
      <TresPointLight :position="lightA" :intensity="3.1" color="#00f2ff" :distance="20" />
      <TresPointLight :position="lightB" :intensity="1.8" color="#5adfff" :distance="15" />
      <TresPointLight :position="lightC" :intensity="0.85" color="#7aebff" :distance="12" />

      <HudHoloAtmosphereField :reduced-motion="reducedMotion" />

      <EffectComposerPmndrs>
        <BloomPmndrs
          :intensity="reducedMotion ? 0.2 : 0.45"
          :luminance-threshold="0.4"
          :luminance-smoothing="0.55"
          :mipmap-blur="true"
        />
        <VignettePmndrs :offset="0.32" :darkness="0.55" />
      </EffectComposerPmndrs>
    </TresCanvas>
  </div>
</template>
