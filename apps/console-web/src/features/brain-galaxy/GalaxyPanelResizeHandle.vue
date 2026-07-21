<script setup lang="ts">
defineProps<{
  edge: 'left' | 'right';
  label: string;
  valueMin: number;
  valueMax: number;
  valueNow: number;
}>();

const emit = defineEmits<{
  mousedown: [event: MouseEvent];
  keydown: [event: KeyboardEvent];
  dblclick: [];
}>();
</script>

<template>
  <div
    class="galaxy-panel__resize-handle"
    :class="
      edge === 'left'
        ? 'galaxy-panel__resize-handle--left-edge'
        : 'galaxy-panel__resize-handle--right-edge'
    "
    role="separator"
    aria-orientation="vertical"
    :aria-label="label"
    title="Drag or use arrow keys to resize. Enter or double-click to reset."
    tabindex="0"
    :aria-valuemin="valueMin"
    :aria-valuemax="valueMax"
    :aria-valuenow="valueNow"
    @mousedown="emit('mousedown', $event)"
    @keydown="emit('keydown', $event)"
    @dblclick="emit('dblclick')"
  >
    <span class="galaxy-panel__resize-grip" aria-hidden="true" />
  </div>
</template>
