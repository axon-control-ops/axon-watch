<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { TresCanvas } from '@tresjs/core';
import { BloomPmndrs, EffectComposerPmndrs } from '@tresjs/post-processing';
import { Vector3 } from 'three';

import { probeWebGlAvailability } from '../brain-galaxy/webgl-availability';
import HudHoloDust from './HudHoloDust.vue';
import HudHoloSignalLattice from './HudHoloSignalLattice.vue';
import HudHoloSlab from './HudHoloSlab.vue';
import type { HudHoloSignal, HudHoloTone } from './hud-holo-tones';

const props = withDefaults(
  defineProps<{
    tone?: HudHoloTone;
    label?: string;
    /** panel = tall sidebar; module = Mission Control mosaic blocks */
    variant?: 'panel' | 'module';
    /** Live Tres signal pads (fleet tiles / task buckets). */
    signals?: HudHoloSignal[];
  }>(),
  {
    tone: 'nominal',
    label: 'holo-panel',
    variant: 'panel',
    signals: () => [],
  },
);

const webglOk = ref(false);
const reducedMotion = ref(false);
const parallaxX = ref(0);
const parallaxY = ref(0);
const cameraPosition = new Vector3(0, 0, 5.8);

const shellClass = computed(() => ({
  'hud-holo-shell--webgl': webglOk.value,
  'hud-holo-shell--css-fallback': !webglOk.value,
  'hud-holo-shell--module': props.variant === 'module',
  [`hud-holo-shell--${props.tone}`]: true,
}));

const bloomIntensity = computed(() => {
  if (reducedMotion.value) {
    return 0.35;
  }
  return props.variant === 'module' ? 0.85 : 1.15;
});

const hasSignals = computed(() => (props.signals?.length ?? 0) > 0);

function onPointerMove(event: PointerEvent): void {
  if (reducedMotion.value || !webglOk.value) {
    return;
  }
  const target = event.currentTarget as HTMLElement;
  const rect = target.getBoundingClientRect();
  if (rect.width < 1 || rect.height < 1) {
    return;
  }
  parallaxX.value = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  parallaxY.value = -(((event.clientY - rect.top) / rect.height) * 2 - 1);
}

function onPointerLeave(): void {
  parallaxX.value = 0;
  parallaxY.value = 0;
}

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
    class="hud-holo-shell"
    :class="shellClass"
    :data-holo-label="label"
    :data-holo-engine="webglOk ? 'tres' : 'css'"
    :data-holo-webgl="webglOk ? '1' : '0'"
    :data-holo-variant="variant"
    @pointermove="onPointerMove"
    @pointerleave="onPointerLeave"
  >
    <div
      v-if="webglOk"
      class="hud-holo-shell__canvas-host"
      aria-hidden="true"
    >
      <TresCanvas
        class="hud-holo-shell__canvas"
        :alpha="true"
        :clear-color="'#00000000'"
        :window-size="false"
        render-mode="always"
      >
        <TresPerspectiveCamera :position="cameraPosition" :fov="32" />
        <TresAmbientLight :intensity="0.65" />
        <HudHoloSlab
          :tone="tone"
          :parallax-x="parallaxX"
          :parallax-y="parallaxY"
          :reduced-motion="reducedMotion"
        />
        <HudHoloSignalLattice
          v-if="hasSignals"
          :signals="signals"
          :reduced-motion="reducedMotion"
          :offset-y="variant === 'module' ? -0.35 : -0.55"
        />
        <HudHoloDust :reduced-motion="reducedMotion" />
        <EffectComposerPmndrs>
          <BloomPmndrs
            :intensity="bloomIntensity"
            :luminance-threshold="0.2"
            :luminance-smoothing="0.4"
            :mipmap-blur="true"
          />
        </EffectComposerPmndrs>
      </TresCanvas>
    </div>
    <div class="hud-holo-shell__glow" aria-hidden="true" />
    <div class="hud-holo-shell__content">
      <slot />
    </div>
  </div>
</template>
