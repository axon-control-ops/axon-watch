<script setup lang="ts">
import { computed, ref } from 'vue';

import type { AgentQuestionOption } from '../../lib/agent-question-view';
import { submitQuestionAnswer } from '../../lib/submit-question-answer';
import { useShellStore } from '../../stores/shell';

const props = defineProps<{
  prompt: string;
  options: AgentQuestionOption[];
  live?: boolean;
  messageId?: string;
  /** When set, render Cursor-like collapsed answered card. */
  answeredOption?: AgentQuestionOption | null;
}>();

const shell = useShellStore();
const selectedId = ref(props.answeredOption?.id || props.options[0]?.id || '');
const submitting = ref(false);
const error = ref('');
const locallyAnswered = ref<AgentQuestionOption | null>(null);

const resolvedAnswer = computed(
  () => locallyAnswered.value ?? props.answeredOption ?? null,
);
const isAnswered = computed(() => Boolean(resolvedAnswer.value) && !props.live);

const radioGroupName = computed(
  () => `axon-agent-question-${props.prompt.slice(0, 40).replace(/\W+/g, '-').toLowerCase()}`,
);

async function continueWithSelection(): Promise<void> {
  const option = props.options.find((entry) => entry.id === selectedId.value) ?? props.options[0];
  if (!option || submitting.value || props.live || isAnswered.value) {
    return;
  }
  submitting.value = true;
  error.value = '';
  try {
    locallyAnswered.value = option;
    await submitQuestionAnswer(shell, {
      workspaceId: shell.currentWorkspace?.workspace_id,
      option,
      prompt: props.prompt,
      messageId: props.messageId,
    });
  } catch (err) {
    locallyAnswered.value = null;
    error.value = err instanceof Error ? err.message : 'Unable to submit choice.';
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <div
    class="agent-block agent-block--question"
    :class="{ 'agent-block--question-answered': isAnswered }"
    role="group"
    :aria-label="prompt"
  >
    <template v-if="isAnswered && resolvedAnswer">
      <p class="agent-block__question-kicker">Answered</p>
      <p class="agent-block__question-prompt">{{ prompt }}</p>
      <p class="agent-block__question-answered-choice">
        <span class="agent-block__question-id">{{ resolvedAnswer.id }}</span>
        <span class="agent-block__question-label">{{ resolvedAnswer.label }}</span>
      </p>
    </template>
    <template v-else>
      <p class="agent-block__question-kicker">Question</p>
      <p class="agent-block__question-prompt">{{ prompt }}</p>
      <div class="agent-block__question-options">
        <label
          v-for="option in options"
          :key="option.id"
          class="agent-block__question-option"
          :class="{ 'agent-block__question-option--selected': selectedId === option.id }"
        >
          <input
            v-model="selectedId"
            class="agent-block__question-radio"
            type="radio"
            :name="radioGroupName"
            :value="option.id"
            :disabled="live || submitting"
          >
          <span class="agent-block__question-id">{{ option.id }}</span>
          <span class="agent-block__question-label">{{ option.label }}</span>
        </label>
      </div>
      <div class="agent-block__question-actions">
        <button
          type="button"
          class="agent-block__question-continue"
          :disabled="live || submitting || !selectedId"
          @click="continueWithSelection"
        >
          {{ submitting ? 'Sending…' : live ? 'Waiting…' : 'Continue' }}
        </button>
      </div>
      <p
        v-if="error"
        class="agent-block__question-error"
      >
        {{ error }}
      </p>
    </template>
  </div>
</template>
