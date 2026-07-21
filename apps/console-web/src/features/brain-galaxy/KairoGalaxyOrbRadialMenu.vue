<script setup lang="ts">
import { computed } from 'vue';

import {
  ORB_RADIAL_MENU_ITEMS,
  orbRadialMenuItemPosition,
  type OrbRadialMenuAction,
} from './galaxy-orb-radial-menu';

const props = defineProps<{
  open: boolean;
  radiusPx?: number;
}>();

const emit = defineEmits<{
  select: [action: OrbRadialMenuAction];
  close: [];
}>();

const radius = computed(() => props.radiusPx ?? 92);

const positionedItems = computed(() =>
  ORB_RADIAL_MENU_ITEMS.map((item) => ({
    ...item,
    position: orbRadialMenuItemPosition(item.angleDeg, radius.value),
  })),
);
</script>

<template>
  <div
    v-if="open"
    class="kairo-galaxy-orb-radial-menu"
    role="menu"
    aria-label="VAXON command ring"
    @keydown.esc.prevent="emit('close')"
  >
    <div class="kairo-galaxy-orb-radial-menu__ring" aria-hidden="true" />
    <div class="kairo-galaxy-orb-radial-menu__core-glow" aria-hidden="true" />

    <button
      v-for="item in positionedItems"
      :key="item.id"
      type="button"
      class="kairo-galaxy-orb-radial-menu__segment"
      role="menuitem"
      :style="{
        '--orb-radial-x': `${item.position.x}px`,
        '--orb-radial-y': `${item.position.y}px`,
      }"
      :title="item.detail"
      :aria-label="`${item.label}. ${item.detail}`"
      @click.stop="emit('select', item.id)"
    >
      <span class="kairo-galaxy-orb-radial-menu__segment-glyph">{{ item.shortLabel }}</span>
      <span class="kairo-galaxy-orb-radial-menu__segment-label">{{ item.label }}</span>
    </button>
  </div>
</template>
