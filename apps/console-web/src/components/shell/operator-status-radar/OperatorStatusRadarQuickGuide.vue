<script setup lang="ts">
import type {
  OperatorQuickGuide,
  OperatorQuickGuideActionId,
} from '../../../lib/operator-quick-guide';

defineProps<{
  guide: OperatorQuickGuide;
  terminalVisible: boolean;
  standalone?: boolean;
}>();

const emit = defineEmits<{
  action: [actionId: OperatorQuickGuideActionId];
}>();
</script>

<template>
  <section
    class="operator-status-radar-panel__guide"
    :class="{
      'operator-status-radar-panel__guide--standalone': standalone,
      'operator-status-radar-panel__guide--terminal-hidden': !terminalVisible,
      'operator-status-radar-panel__guide--attention': guide.tone === 'attention',
    }"
    aria-label="What to do next"
  >
    <div class="operator-status-radar-panel__guide-head">
      <p class="operator-status-radar-panel__guide-title">{{ guide.title }}</p>
      <div
        v-if="guide.actions.length"
        class="operator-status-radar-panel__guide-actions"
        role="group"
        aria-label="Quick actions"
      >
        <button
          v-for="action in guide.actions"
          :key="action.id"
          type="button"
          class="operator-status-radar-panel__guide-action"
          @click="emit('action', action.id)"
        >
          {{ action.label }}
        </button>
      </div>
    </div>
    <ol class="operator-status-radar-panel__guide-steps">
      <li v-for="(step, index) in guide.steps" :key="index">{{ step }}</li>
    </ol>
  </section>
</template>
