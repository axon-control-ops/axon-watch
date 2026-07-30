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
    /** `composer` = load into bottom dock (commands). `inline` = emit edit for in-place YOU editing. */
    editBehavior?: 'composer' | 'inline';
    /** Text labels (commands) vs Cursor-style icon chrome (sticky YOU). */
    variant?: 'text' | 'icons';
  }>(),
  {
    editTitle: 'Edit message',
    editAriaLabel: 'Edit message',
    showResend: false,
    editBehavior: 'composer',
    variant: 'text',
  },
);

const emit = defineEmits<{
  edit: [];
  resend: [];
}>();

const shell = useShellStore();
const resendDisabled = computed(
  () => shell.commandMutationState === 'submitting' || shell.agentStreamActive,
);

function onEdit(): void {
  if (props.editBehavior === 'inline') {
    emit('edit');
    return;
  }
  restoreOperatorTextToComposer(props.text);
}

function onResend(): void {
  if (props.editBehavior === 'inline') {
    emit('resend');
    return;
  }
  void resendOperatorMessage(props.text);
}
</script>

<template>
  <div
    class="conversation-seam__message-actions"
    :class="{ 'conversation-seam__message-actions--icons': variant === 'icons' }"
  >
    <button
      type="button"
      class="conversation-seam__meta-button conversation-seam__edit-button"
      :class="{ 'conversation-seam__meta-button--icon': variant === 'icons' }"
      :title="editTitle"
      :aria-label="editAriaLabel"
      @click.stop="onEdit"
    >
      <template v-if="variant === 'icons'">
        <svg
          class="conversation-seam__action-icon"
          width="14"
          height="14"
          viewBox="0 0 16 16"
          fill="none"
          stroke="currentColor"
          stroke-width="1.4"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <path d="M9.6 3.35 12.65 6.4" />
          <path d="M3.2 12.8l.75-3.35L10.9 2.5a1.15 1.15 0 0 1 1.63 0l.97.97a1.15 1.15 0 0 1 0 1.63L6.55 12.05z" />
          <path d="M3.2 12.8h9.4" />
        </svg>
      </template>
      <template v-else>Edit</template>
    </button>
    <button
      v-if="showResend"
      type="button"
      class="conversation-seam__meta-button conversation-seam__resend-button"
      :class="{ 'conversation-seam__meta-button--icon': variant === 'icons' }"
      title="Retry — submit this request again"
      aria-label="Retry request"
      :disabled="resendDisabled"
      @click.stop="onResend"
    >
      <template v-if="variant === 'icons'">
        <svg
          class="conversation-seam__action-icon"
          width="14"
          height="14"
          viewBox="0 0 16 16"
          fill="none"
          stroke="currentColor"
          stroke-width="1.4"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <path d="M3.1 6.2A5.1 5.1 0 0 1 12.4 5.4" />
          <path d="M12.9 9.8A5.1 5.1 0 0 1 3.6 10.6" />
          <path d="M12.4 2.85v2.7h-2.7" />
          <path d="M3.6 13.15v-2.7h2.7" />
        </svg>
      </template>
      <template v-else>Resend</template>
    </button>
  </div>
</template>
