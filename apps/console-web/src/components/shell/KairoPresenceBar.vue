<script setup lang="ts">
import { computed } from 'vue';

import OperatorPersonaMark from '../../components/OperatorPersonaMark.vue';
import { kairoPresenceModuleParts } from '../../lib/mockup-shell-view';
import type { KairoPresenceState } from '../../lib/kairo-presence';

const props = defineProps<{
  state: KairoPresenceState;
  speechActive?: boolean;
  paused?: boolean;
  compact?: boolean;
}>();

const emit = defineEmits<{
  action: [];
}>();

const parts = computed(() => kairoPresenceModuleParts(props.state));

const showWaveform = computed(() => {
  if (props.paused) {
    return false;
  }
  return Boolean(props.speechActive) || props.state === 'speaking';
});

const actionHint = computed(() => {
  if (props.paused) {
    return 'Click to continue speaking';
  }
  if (props.speechActive || props.state === 'speaking') {
    return 'Click to pause';
  }
  if (props.state === 'alerting') {
    return 'Open Attention';
  }
  return 'Open operator briefing';
});

const ariaLabel = computed(
  () => `${parts.value.title} ${parts.value.subtitle}. ${actionHint.value}`,
);
</script>

<template>
  <button
    type="button"
    class="kairo-presence-module"
    :class="{
      [`kairo-presence-module--${state}`]: true,
      'kairo-presence-module--speech-live': speechActive && !paused,
      'kairo-presence-module--compact': compact,
      'kairo-presence-module--chip': compact,
    }"
    :aria-label="ariaLabel"
    @click="emit('action')"
  >
    <span
      v-if="!compact"
      class="kairo-presence-module__corner kairo-presence-module__corner--tl"
      aria-hidden="true"
    />
    <span
      v-if="!compact"
      class="kairo-presence-module__corner kairo-presence-module__corner--br"
      aria-hidden="true"
    />

    <span v-if="!compact" class="kairo-presence-module__radar" aria-hidden="true">
      <span class="kairo-presence-module__radar-ring kairo-presence-module__radar-ring--outer" />
      <span class="kairo-presence-module__radar-ring kairo-presence-module__radar-ring--mid" />
      <span class="kairo-presence-module__radar-arc" />
      <span class="kairo-presence-module__radar-tick kairo-presence-module__radar-tick--n" />
      <span class="kairo-presence-module__radar-tick kairo-presence-module__radar-tick--e" />
      <span class="kairo-presence-module__radar-tick kairo-presence-module__radar-tick--s" />
      <span class="kairo-presence-module__radar-tick kairo-presence-module__radar-tick--w" />
    </span>

    <span v-if="compact" class="kairo-presence-module__mark" aria-hidden="true">
      <OperatorPersonaMark size="xs" />
    </span>

    <span class="kairo-presence-module__copy">
      <span v-if="!compact" class="kairo-presence-module__title persona-title">
        <OperatorPersonaMark size="sm" />
      </span>
      <span class="kairo-presence-module__subtitle">{{ parts.subtitle }}</span>
    </span>

    <span
      v-if="showWaveform"
      class="kairo-presence-module__waveform"
      aria-hidden="true"
    >
      <span class="kairo-presence-module__waveform-axis" />
      <span /><span /><span /><span /><span /><span /><span /><span /><span />
    </span>
  </button>
</template>
