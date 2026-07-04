<script setup lang="ts">
import { computed } from 'vue';

import {
  kairoPresenceLabel,
  type KairoPresenceState,
} from '../lib/kairo-presence';

const props = defineProps<{
  state: KairoPresenceState;
}>();

const label = computed(() => kairoPresenceLabel(props.state));
</script>

<template>
  <button
    type="button"
    class="kairo-chip"
    :class="`kairo-chip--${state}`"
    :aria-label="label"
    title="Open KAIRO briefing"
  >
    <span class="kairo-chip__pulse" aria-hidden="true" />
    <span class="kairo-chip__label">{{ label }}</span>
  </button>
</template>
