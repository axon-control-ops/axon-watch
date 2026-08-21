<script setup lang="ts">
import { computed } from 'vue';

import { describeApprovalBanner } from '../../../lib/run-approval-view';

const props = defineProps<{
  show: boolean;
  currentStep?: string | null;
  canApprove: boolean;
  rejectPending: boolean;
}>();

const emit = defineEmits<{
  approve: [];
  reject: [];
}>();

const view = computed(() => describeApprovalBanner(props.currentStep));
</script>

<template>
  <div
    v-if="show"
    class="agent-dock-composer__approval-banner"
    :class="{ 'agent-dock-composer__approval-banner--ask-block': view.isAskBlock }"
    role="status"
  >
    <p class="agent-dock-composer__approval-copy">
      {{ view.bannerCopy }}
    </p>
    <p v-if="view.isAskBlock" class="agent-dock-composer__approval-hint">
      To answer, send your reply in the composer below — these buttons do not answer the question.
    </p>
    <div class="agent-dock-composer__approval-actions">
      <button
        type="button"
        class="agent-dock-composer__approval-btn agent-dock-composer__approval-btn--approve"
        :disabled="!canApprove"
        :title="view.isAskBlock ? 'Resumes the run without sending an answer' : ''"
        @click="emit('approve')"
      >
        {{ view.approveLabel }}
      </button>
      <button
        type="button"
        class="agent-dock-composer__approval-btn agent-dock-composer__approval-btn--reject"
        :disabled="rejectPending"
        :title="view.rejectWarning"
        @click="emit('reject')"
      >
        {{ view.rejectLabel }}
      </button>
    </div>
  </div>
</template>
