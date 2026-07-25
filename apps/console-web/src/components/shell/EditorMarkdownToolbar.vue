<script setup lang="ts">
defineProps<{
  previewEnabled: boolean;
  planId: string;
  buildingPlan: boolean;
  buildPlanError: string;
  canBuildPlan: boolean;
}>();

const emit = defineEmits<{
  setPreview: [enabled: boolean];
  buildPlan: [];
}>();
</script>

<template>
  <div class="editor-markdown-toolbar">
    <div
      class="conversation-seam__markdown-mode-toggle editor-markdown-toolbar__toggle"
      role="group"
      aria-label="Editor markdown view mode"
    >
      <button
        type="button"
        class="conversation-seam__markdown-mode-button"
        :class="{ 'conversation-seam__markdown-mode-button--active': previewEnabled }"
        :aria-pressed="previewEnabled"
        @click="emit('setPreview', true)"
      >
        Preview
      </button>
      <button
        type="button"
        class="conversation-seam__markdown-mode-button"
        :class="{ 'conversation-seam__markdown-mode-button--active': !previewEnabled }"
        :aria-pressed="!previewEnabled"
        @click="emit('setPreview', false)"
      >
        Raw
      </button>
    </div>
    <div
      v-if="planId"
      class="editor-markdown-toolbar__plan-actions"
    >
      <button
        type="button"
        class="editor-markdown-toolbar__build-plan"
        :disabled="buildingPlan || !canBuildPlan"
        @click="emit('buildPlan')"
      >
        {{ buildingPlan ? 'Building…' : 'Build Plan' }}
      </button>
      <span
        v-if="buildPlanError"
        class="editor-markdown-toolbar__build-error"
      >{{ buildPlanError }}</span>
    </div>
  </div>
</template>
