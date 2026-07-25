<script setup lang="ts">
defineProps<{
  tag?: keyof HTMLElementTagNameMap;
  panelClass?: string;
}>();
</script>

<template>
  <component
    :is="tag ?? 'section'"
    class="vault-hud-panel hud-panel-frame"
    :class="panelClass"
  >
    <span class="hud-panel-frame__corner hud-panel-frame__corner--tl" aria-hidden="true" />
    <span class="hud-panel-frame__corner hud-panel-frame__corner--tr" aria-hidden="true" />
    <span class="hud-panel-frame__corner hud-panel-frame__corner--bl" aria-hidden="true" />
    <span class="hud-panel-frame__corner hud-panel-frame__corner--br" aria-hidden="true" />
    <div class="vault-hud-panel__body">
      <slot />
    </div>
  </component>
</template>
