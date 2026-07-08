<script setup lang="ts">
import { computed } from 'vue';

import {
  kairoPresenceSubtitle,
  type KairoPresenceState,
} from '../lib/kairo-presence';
import OperatorPersonaMark from './OperatorPersonaMark.vue';

const props = defineProps<{
  state: KairoPresenceState;
}>();

const emit = defineEmits<{
  openBriefing: [];
}>();

const subtitle = computed(() => kairoPresenceSubtitle(props.state));
const showWaveform = computed(
  () =>
    props.state === 'observing' ||
    props.state === 'listening' ||
    props.state === 'speaking' ||
    props.state === 'thinking' ||
    props.state === 'alerting',
);
</script>

<template>
  <button
    type="button"
    class="kairo-chip"
    :class="`kairo-chip--${state}`"
    :aria-label="`${subtitle} operator presence`"
    title="Open operator briefing"
    @click="emit('openBriefing')"
  >
    <span class="kairo-chip__pulse" aria-hidden="true" />
    <span v-if="showWaveform" class="kairo-chip__waveform" aria-hidden="true">
      <span />
      <span />
      <span />
      <span />
    </span>
    <span class="kairo-chip__label persona-title">
      <OperatorPersonaMark size="xs" />
      <span class="kairo-chip__subtitle">{{ subtitle }}</span>
    </span>
  </button>
</template>
