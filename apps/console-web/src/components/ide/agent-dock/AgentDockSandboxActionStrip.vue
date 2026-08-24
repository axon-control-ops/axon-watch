<script setup lang="ts">
import { computed } from 'vue';

import { sandboxStripDetailCopy } from '../../../lib/sandbox-session-view';

const props = defineProps<{
  show: boolean;
  dirty: boolean;
  pending: boolean;
  message?: string | null;
  previewUrl?: string;
  collapsed?: boolean;
}>();

const emit = defineEmits<{
  review: [];
  startPreview: [];
  stopPreview: [];
  restartPreview: [];
  publish: [];
  discard: [];
  toggleCollapsed: [];
}>();

/**
 * Collapsed still has to carry the two facts an operator acts on — whether
 * there are unpromoted changes and whether a preview is live — otherwise
 * collapsing it hides exactly the state it exists to report.
 */
const summary = computed(() => {
  const parts = [props.dirty ? 'unpromoted changes' : 'clean'];
  if (props.previewUrl) parts.push('preview running');
  return parts.join(' · ');
});
</script>

<template>
  <div
    v-if="show"
    class="agent-dock-composer__sandbox-strip"
    :class="{ 'agent-dock-composer__sandbox-strip--collapsed': collapsed }"
    role="status"
  >
    <button
      type="button"
      class="agent-dock-composer__sandbox-strip-toggle"
      :aria-expanded="!collapsed"
      :title="collapsed ? 'Expand Sandbox changes' : 'Collapse Sandbox changes'"
      @click="emit('toggleCollapsed')"
    >
      <span class="agent-dock-composer__sandbox-strip-chevron">{{ collapsed ? '▸' : '▾' }}</span>
      <span class="agent-dock-composer__sandbox-strip-kicker">Sandbox changes</span>
      <span v-if="collapsed" class="agent-dock-composer__sandbox-strip-summary">{{ summary }}</span>
    </button>

    <template v-if="!collapsed">
      <div class="agent-dock-composer__sandbox-strip-copy">
        <span class="agent-dock-composer__sandbox-strip-detail">
          {{ sandboxStripDetailCopy(dirty) }}
        </span>
        <span v-if="message" class="agent-dock-composer__sandbox-strip-message">
          {{ message }}
        </span>
        <a
          v-if="previewUrl"
          class="agent-dock-composer__sandbox-strip-link"
          :href="previewUrl"
          target="_blank"
          rel="noopener noreferrer"
        >
          Open sandbox preview — {{ previewUrl }}
        </a>
      </div>
      <div class="agent-dock-composer__sandbox-strip-actions">
        <button
          type="button"
          class="agent-dock-composer__sandbox-strip-btn agent-dock-composer__sandbox-strip-btn--primary"
          :disabled="pending"
          @click="emit('review')"
        >
          {{ pending ? 'Checking…' : 'Review / Preview' }}
        </button>
        <button
          type="button"
          class="agent-dock-composer__sandbox-strip-btn"
          :disabled="pending"
          :title="
            previewUrl
              ? 'Stop the dev server running against the sandbox checkout'
              : 'Run this workspace\'s dev server against the sandbox checkout, on a spare port'
          "
          @click="previewUrl ? emit('stopPreview') : emit('startPreview')"
        >
          {{ previewUrl ? 'Stop preview' : 'Run preview' }}
        </button>
        <button
          v-if="previewUrl"
          type="button"
          class="agent-dock-composer__sandbox-strip-btn"
          :disabled="pending"
          title="Stop and start the sandbox preview — picks up config changes a dev server cannot hot-reload"
          @click="emit('restartPreview')"
        >
          Restart
        </button>
        <button
          type="button"
          class="agent-dock-composer__sandbox-strip-btn"
          :disabled="pending || !dirty"
          @click="emit('publish')"
        >
          Publish
        </button>
        <button
          type="button"
          class="agent-dock-composer__sandbox-strip-btn agent-dock-composer__sandbox-strip-btn--danger"
          :disabled="pending"
          @click="emit('discard')"
        >
          Discard
        </button>
      </div>
    </template>
  </div>
</template>
