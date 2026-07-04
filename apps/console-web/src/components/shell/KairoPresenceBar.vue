<script setup lang="ts">
import { computed } from 'vue';

import { kairoPresenceModuleParts } from '../../lib/mockup-shell-view';
import type { KairoPresenceState } from '../../lib/kairo-presence';

const props = defineProps<{
  state: KairoPresenceState;
}>();

const emit = defineEmits<{
  openBriefing: [];
}>();

const parts = computed(() => kairoPresenceModuleParts(props.state));
const ariaLabel = computed(() => `${parts.value.title} ${parts.value.subtitle}`);
</script>

<template>
  <button
    type="button"
    class="kairo-presence-module"
    :class="`kairo-presence-module--${state}`"
    :aria-label="ariaLabel"
    @click="emit('openBriefing')"
  >
    <span class="kairo-presence-module__corner kairo-presence-module__corner--tl" aria-hidden="true" />
    <span class="kairo-presence-module__corner kairo-presence-module__corner--br" aria-hidden="true" />

    <span class="kairo-presence-module__radar" aria-hidden="true">
      <span class="kairo-presence-module__radar-ring kairo-presence-module__radar-ring--outer" />
      <span class="kairo-presence-module__radar-ring kairo-presence-module__radar-ring--mid" />
      <span class="kairo-presence-module__radar-arc" />
      <span class="kairo-presence-module__radar-tick kairo-presence-module__radar-tick--n" />
      <span class="kairo-presence-module__radar-tick kairo-presence-module__radar-tick--e" />
      <span class="kairo-presence-module__radar-tick kairo-presence-module__radar-tick--s" />
      <span class="kairo-presence-module__radar-tick kairo-presence-module__radar-tick--w" />
    </span>

    <span class="kairo-presence-module__copy">
      <span class="kairo-presence-module__title">{{ parts.title }}</span>
      <span class="kairo-presence-module__subtitle">{{ parts.subtitle }}</span>
    </span>

    <span class="kairo-presence-module__waveform" aria-hidden="true">
      <span class="kairo-presence-module__waveform-axis" />
      <span /><span /><span /><span /><span /><span /><span /><span /><span />
    </span>
  </button>
</template>
