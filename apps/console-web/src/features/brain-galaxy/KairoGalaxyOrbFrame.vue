<script setup lang="ts">
import { ref } from 'vue';

import KairoGalaxyOrbAura from './KairoGalaxyOrbAura.vue';

defineProps<{
  dragging: boolean;
  placementMode: 'viewport' | 'embedded';
  chromeLive: boolean;
  ideClose: boolean;
  anchorStyle: Record<string, string> | undefined;
  personaName: string;
}>();

const emit = defineEmits<{
  hide: [];
}>();

const rootEl = ref<HTMLElement | null>(null);
defineExpose({ rootEl });
</script>

<template>
  <div
    ref="rootEl"
    class="brain-galaxy-stage__jarvis-float brain-galaxy-stage__jarvis-float--mockup"
    data-voice-orb-root
    :class="{
      'brain-galaxy-stage__jarvis-float--dragging': dragging,
      'brain-galaxy-stage__jarvis-float--viewport': placementMode === 'viewport',
      'brain-galaxy-stage__jarvis-float--embedded': placementMode === 'embedded',
      'brain-galaxy-stage__jarvis-float--chrome-live': chromeLive,
      'brain-galaxy-stage__jarvis-float--ide': ideClose,
    }"
    :style="placementMode === 'viewport' ? anchorStyle : undefined"
  >
    <KairoGalaxyOrbAura />
    <button
      v-if="ideClose"
      type="button"
      class="kairo-galaxy-orb__close"
      :aria-label="`Hide ${personaName} voice orb`"
      title="Hide voice orb"
      @click.stop="emit('hide')"
    >
      ×
    </button>
    <slot />
  </div>
</template>
