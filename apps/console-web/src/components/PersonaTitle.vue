<script setup lang="ts">
import OperatorPersonaMark from './OperatorPersonaMark.vue';
import type { PersonaMarkSize } from '../lib/operator-persona-mark-view';

withDefaults(
  defineProps<{
    suffix?: string;
    markSize?: PersonaMarkSize;
    uppercase?: boolean;
  }>(),
  {
    suffix: '',
    markSize: 'sm',
    uppercase: true,
  },
);
</script>

<template>
  <span class="persona-title" :class="{ 'persona-title--uppercase': uppercase }">
    <OperatorPersonaMark :size="markSize" />
    <span v-if="suffix" class="persona-title__suffix">{{ suffix }}</span>
  </span>
</template>
