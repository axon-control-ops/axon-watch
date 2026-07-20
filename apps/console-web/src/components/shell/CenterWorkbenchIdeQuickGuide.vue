<script setup lang="ts">
import type { IdeQuickGuide, IdeQuickGuideActionId } from '../../lib/ide-quick-guide';

defineProps<{
  guide: IdeQuickGuide;
  withEditor: boolean;
}>();

const emit = defineEmits<{
  action: [actionId: IdeQuickGuideActionId];
}>();
</script>

<template>
  <section
    class="center-workbench__ide-guide"
    :class="{
      'center-workbench__ide-guide--with-editor': withEditor,
      [`center-workbench__ide-guide--${guide.tone}`]: true,
    }"
    role="status"
    :aria-live="guide.tone === 'neutral' ? 'off' : 'polite'"
    aria-label="IDE tips"
  >
    <div class="center-workbench__ide-guide-head">
      <p class="center-workbench__ide-guide-title">{{ guide.title }}</p>
      <div
        v-if="guide.actions.length"
        class="center-workbench__ide-guide-actions"
        role="group"
        aria-label="Quick panel actions"
      >
        <button
          v-for="action in guide.actions"
          :key="action.id"
          type="button"
          class="center-workbench__ide-guide-action"
          @click="emit('action', action.id)"
        >
          {{ action.label }}
        </button>
      </div>
    </div>
    <ol class="center-workbench__ide-guide-steps">
      <li v-for="(step, index) in guide.steps" :key="index">{{ step }}</li>
    </ol>
  </section>
</template>
