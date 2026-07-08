<script setup lang="ts">
import { computed } from 'vue';

import { OPERATOR_PERSONA_MARK } from '../lib/operator-persona-name';
import type { PersonaMarkSize } from '../lib/operator-persona-mark-view';

const props = withDefaults(
  defineProps<{
    size?: PersonaMarkSize | number;
  }>(),
  {
    size: 'md',
  },
);

const sizeClass = computed(() =>
  typeof props.size === 'string' ? `persona-glyph--${props.size}` : 'persona-glyph--custom',
);

const customStyle = computed(() =>
  typeof props.size === 'number' ? { fontSize: `${props.size}px` } : undefined,
);
</script>

<template>
  <span
    class="persona-glyph"
    :class="sizeClass"
    :style="customStyle"
    aria-hidden="true"
  >{{ OPERATOR_PERSONA_MARK }}</span>
</template>
