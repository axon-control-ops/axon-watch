<script setup lang="ts">
import BriefingSeamIcon from './BriefingSeamIcon.vue';

defineProps<{
  title: string;
  subtitle?: string | null;
  hero?: boolean;
  seamClass?: string;
  seamId?: string;
  collapsed?: boolean;
  compactSummary?: string | null;
  collapsible?: boolean;
  emphasized?: boolean;
  alert?: boolean;
  showViewAll?: boolean;
  headerMenu?: boolean;
  titleGlyph?: 'briefing';
}>();

const emit = defineEmits<{
  toggle: [];
}>();
</script>

<template>
  <section
    :id="seamId"
    class="hud-seam"
    :class="[
      seamClass,
      {
        'hud-seam--hero': hero,
        'hud-seam--collapsed': collapsed,
        'hud-seam--emphasized': emphasized,
        'hud-seam--alert': alert,
      },
    ]"
  >
    <span class="hud-seam__corner hud-seam__corner--tl" aria-hidden="true" />
    <span class="hud-seam__corner hud-seam__corner--tr" aria-hidden="true" />
    <span class="hud-seam__corner hud-seam__corner--bl" aria-hidden="true" />
    <span class="hud-seam__corner hud-seam__corner--br" aria-hidden="true" />

    <div class="hud-seam__header">
      <div class="hud-seam__title-block">
        <BriefingSeamIcon v-if="titleGlyph === 'briefing'" />
        <p class="hud-seam__title">{{ title }}</p>
        <p v-if="subtitle" class="hud-seam__subtitle">{{ subtitle }}</p>
      </div>
      <div class="hud-seam__header-actions">
        <button v-if="headerMenu" type="button" class="hud-seam__menu" aria-label="Open menu">
          <span aria-hidden="true" />
          <span aria-hidden="true" />
          <span aria-hidden="true" />
        </button>
        <button v-else-if="showViewAll" type="button" class="hud-seam__view-all">
          <span>VIEW ALL</span>
          <span class="hud-seam__view-all-icon" aria-hidden="true">↗</span>
        </button>
        <button
          v-if="collapsible"
          type="button"
          class="hud-seam__toggle"
          :aria-expanded="!collapsed"
          @click="emit('toggle')"
        >
          {{ collapsed ? 'Expand' : 'Collapse' }}
        </button>
      </div>
    </div>

    <p v-if="collapsed && compactSummary" class="hud-seam__compact">
      {{ compactSummary }}
    </p>

    <div v-show="!collapsed" class="hud-seam__body">
      <slot />
    </div>
  </section>
</template>
