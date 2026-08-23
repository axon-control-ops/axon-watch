<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{ count: number }>();
defineEmits<{ open: [] }>();

const label = computed(() =>
  props.count ? `${props.count} NEED${props.count === 1 ? 'S' : ''} YOU` : '',
);
</script>

<template>
  <button
    v-if="label"
    type="button"
    class="company-roster__decision-badge"
    aria-live="polite"
    :aria-label="`${label}: open the agent awaiting your decision`"
    @click="$emit('open')"
  >
    {{ label }}
  </button>
</template>
