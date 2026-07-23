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
  // #region agent log
  fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Debug-Session-Id': 'fc0b35',
    },
    body: JSON.stringify({
      sessionId: 'fc0b35',
      runId: 'tres-atmosphere',
      hypothesisId: 'H-concept',
      location: 'HudHoloAtmosphere.vue:onMounted',
      message: 'shell Tres atmosphere + bloom',
      data: { webglOk: probe.ok, renderer: probe.renderer, reducedMotion: reducedMotion.value },
      timestamp: Date.now(),
    }),
  }).catch(() => {});
  // #endregion
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
      :clear-color="'#00000000'"
      :window-size="false"
      render-mode="always"
    >
      <TresPerspectiveCamera :position="cameraPosition" :fov="42" />
      <TresAmbientLight :intensity="0.35" />
      <TresPointLight :position="lightA" :intensity="2.4" color="#7aebff" :distance="18" />
      <TresPointLight :position="lightB" :intensity="1.4" color="#5a9fff" :distance="14" />
      <TresPointLight :position="lightC" :intensity="0.9" color="#ff6aa8" :distance="12" />

      <HudHoloAtmosphereField :reduced-motion="reducedMotion" />

      <EffectComposerPmndrs>
        <BloomPmndrs
          :intensity="reducedMotion ? 0.45 : 1.35"
          :luminance-threshold="0.18"
          :luminance-smoothing="0.4"
          :mipmap-blur="true"
        />
        <VignettePmndrs :offset="0.28" :darkness="0.55" />
      </EffectComposerPmndrs>
    </TresCanvas>
  </div>
</template>
