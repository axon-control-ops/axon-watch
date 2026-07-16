<script setup lang="ts">
import type { ComposerAccessTone } from '../../../lib/sandbox-session-view';

defineProps<{
  banner: {
    title: string;
    detail: string;
    glyph: string;
    tone: ComposerAccessTone;
  };
}>();
</script>

<template>
  <div
    class="agent-dock-composer__access-banner"
    :class="`agent-dock-composer__access-banner--${banner.tone}`"
    role="status"
  >
    <span class="agent-dock-composer__access-banner-pulse" aria-hidden="true" />
    <span class="agent-dock-composer__access-banner-copy">
      <span class="agent-dock-composer__access-banner-title">
        {{ banner.title }}
      </span>
      <span class="agent-dock-composer__access-banner-sep" aria-hidden="true">—</span>
      <span class="agent-dock-composer__access-banner-detail">
        {{ banner.detail }}
      </span>
    </span>
    <span
      v-if="banner.tone === 'sandbox' || banner.tone === 'sandbox-full'"
      class="agent-dock-composer__access-banner-tag"
    >Sandbox</span>
  </div>
</template>
