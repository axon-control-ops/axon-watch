<script setup lang="ts">
import { computed } from 'vue';

import { OPERATOR_PERSONA_MARK } from '../lib/operator-persona-name';
import type { PersonaMarkSize } from '../lib/operator-persona-mark-view';

const props = withDefaults(
  defineProps<{
    size?: PersonaMarkSize | number;
    /** Override glyph (e.g. employee initials). Defaults to VAXON mark. */
    mark?: string | null;
  }>(),
  {
    size: 'md',
    mark: null,
  },
);

const sizeClass = computed(() =>
  typeof props.size === 'string' ? `persona-glyph--${props.size}` : 'persona-glyph--custom',
);

const customStyle = computed(() =>
  typeof props.size === 'number' ? { fontSize: `${props.size}px` } : undefined,
);

const glyph = computed(() => {
  const override = props.mark?.trim();
  return override || OPERATOR_PERSONA_MARK;
});
</script>

<template>
  <span
    class="persona-glyph"
    :class="sizeClass"
    :style="customStyle"
    aria-hidden="true"
  >{{ glyph }}</span>
</template>
