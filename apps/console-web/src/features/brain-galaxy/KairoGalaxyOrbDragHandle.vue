<script setup lang="ts">
const emit = defineEmits<{
  pointerdown: [event: PointerEvent];
  pointermove: [event: PointerEvent];
  pointerup: [event: PointerEvent];
  pointercancel: [event: PointerEvent];
}>();
</script>

<template>
  <button
    type="button"
    class="kairo-galaxy-orb__drag-handle"
    aria-label="Move VAXON orb"
    title="Drag to move VAXON"
    @pointerdown.stop.prevent="emit('pointerdown', $event)"
    @pointermove.stop.prevent="emit('pointermove', $event)"
    @pointerup.stop.prevent="emit('pointerup', $event)"
    @pointercancel.stop.prevent="emit('pointercancel', $event)"
  >
    <span class="kairo-galaxy-orb__drag-grip" aria-hidden="true" />
  </button>
</template>
