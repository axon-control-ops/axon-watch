<script setup lang="ts">
import { computed } from 'vue';

import {
  resendOperatorMessage,
  restoreOperatorTextToComposer,
} from '../../lib/operator-message-composer-actions';
import { useShellStore } from '../../stores/shell';

const props = withDefaults(
  defineProps<{
    text: string;
    editTitle?: string;
    editAriaLabel?: string;
    showResend?: boolean;
  }>(),
  {
    editTitle: 'Edit — load this request into the composer',
    editAriaLabel: 'Edit request',
    showResend: false,
  },
);

const shell = useShellStore();
const resendDisabled = computed(
  () => shell.commandMutationState === 'submitting' || shell.agentStreamActive,
);
</script>

<template>
  <div class="conversation-seam__message-actions">
    <button
      type="button"
      class="conversation-seam__meta-button conversation-seam__edit-button"
      :title="editTitle"
      :aria-label="editAriaLabel"
      @click.stop="restoreOperatorTextToComposer(text)"
    >
      Edit
    </button>
    <button
      v-if="showResend"
      type="button"
      class="conversation-seam__meta-button conversation-seam__resend-button"
      title="Resend — submit this request again"
      aria-label="Resend request"
      :disabled="resendDisabled"
      @click.stop="resendOperatorMessage(text)"
    >
      Resend
    </button>
  </div>
</template>
