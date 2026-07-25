<script setup lang="ts">
import { ref, watch } from 'vue';

import type { IdeQuickGuide, IdeQuickGuideActionId } from '../../lib/ide-quick-guide';
import {
  ideQuickGuideActionAriaLabel,
  ideQuickGuideActionIsSecondary,
} from '../../lib/ide-quick-guide';

const props = defineProps<{
  guide: IdeQuickGuide;
  withEditor: boolean;
}>();

const emit = defineEmits<{
  action: [actionId: IdeQuickGuideActionId];
  dismiss: [];
}>();

const expanded = ref(false);

watch(
  () => props.guide.title,
  () => {
    expanded.value = false;
  },
);

function toggleExpanded(): void {
  if (props.guide.steps.length === 0) {
    return;
  }
  expanded.value = !expanded.value;
}
</script>

<template>
  <section
    class="center-workbench__ide-guide"
    :class="{
      'center-workbench__ide-guide--with-editor': withEditor,
      'center-workbench__ide-guide--expanded': expanded,
      [`center-workbench__ide-guide--${guide.tone}`]: true,
    }"
    role="status"
    :aria-live="guide.tone === 'neutral' ? 'off' : 'polite'"
    aria-label="IDE tip"
  >
    <div class="center-workbench__ide-guide-head">
      <button
        type="button"
        class="center-workbench__ide-guide-title-btn"
        :aria-expanded="guide.steps.length ? expanded : undefined"
        :disabled="guide.steps.length === 0"
        @click="toggleExpanded"
      >
        <p class="center-workbench__ide-guide-title">{{ guide.title }}</p>
        <span
          v-if="guide.steps.length"
          class="center-workbench__ide-guide-expand-hint"
        >
          {{ expanded ? 'Hide tips' : 'Tips' }}
        </span>
      </button>
      <div class="center-workbench__ide-guide-toolbar">
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
            :class="{
              'center-workbench__ide-guide-action--secondary': ideQuickGuideActionIsSecondary(
                action.id,
                guide.actions,
              ),
            }"
            :aria-label="ideQuickGuideActionAriaLabel(action)"
            @click="emit('action', action.id)"
          >
            {{ action.label }}
          </button>
        </div>
        <button
          type="button"
          class="center-workbench__ide-guide-dismiss"
          aria-label="Dismiss IDE tip"
          title="Dismiss"
          @click="emit('dismiss')"
        >
          ×
        </button>
      </div>
    </div>
    <ol v-if="expanded && guide.steps.length" class="center-workbench__ide-guide-steps">
      <li v-for="(step, index) in guide.steps" :key="index">{{ step }}</li>
    </ol>
  </section>
</template>
