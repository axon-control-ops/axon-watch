<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import {
  AGENT_QUESTION_OTHER_ID,
  isAgentQuestionOtherOption,
  withOtherQuestionOption,
  type AgentQuestionOption,
} from '../../lib/agent-question-view';
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
const displayOptions = computed(() => withOtherQuestionOption(props.options));
const selectedId = ref(props.answeredOption?.id || displayOptions.value[0]?.id || '');
const otherText = ref(
  props.answeredOption && isAgentQuestionOtherOption(props.answeredOption)
    ? props.answeredOption.label
    : '',
);
const submitting = ref(false);
const error = ref('');
const locallyAnswered = ref<AgentQuestionOption | null>(null);

const resolvedAnswer = computed(
  () => locallyAnswered.value ?? props.answeredOption ?? null,
);
const isAnswered = computed(() => Boolean(resolvedAnswer.value) && !props.live);
const otherSelected = computed(() => {
  const selected = displayOptions.value.find((option) => option.id === selectedId.value);
  return Boolean(selected && isAgentQuestionOtherOption(selected));
});
const canContinue = computed(() => {
  if (!selectedId.value || props.live || submitting.value || isAnswered.value) {
    return false;
  }
  if (otherSelected.value) {
    return otherText.value.trim().length > 0;
  }
  return true;
});

const radioGroupName = computed(
  () => `axon-agent-question-${props.prompt.slice(0, 40).replace(/\W+/g, '-').toLowerCase()}`,
);

watch(
  () => props.options,
  () => {
    if (!displayOptions.value.some((option) => option.id === selectedId.value)) {
      selectedId.value = displayOptions.value[0]?.id || '';
    }
  },
);

async function continueWithSelection(): Promise<void> {
  const option =
    displayOptions.value.find((entry) => entry.id === selectedId.value) ??
    displayOptions.value[0];
  if (!option || !canContinue.value) {
    return;
  }
  const customText = otherSelected.value ? otherText.value.trim() : undefined;
  const answeredOption: AgentQuestionOption =
    otherSelected.value && customText
      ? { id: option.id || AGENT_QUESTION_OTHER_ID, label: customText }
      : option;

  submitting.value = true;
  error.value = '';
  try {
    locallyAnswered.value = answeredOption;
    await submitQuestionAnswer(shell, {
      workspaceId: shell.currentWorkspace?.workspace_id,
      option: answeredOption,
      prompt: props.prompt,
      messageId: props.messageId,
      customText,
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
      <div
        class="agent-block__question-options"
        role="radiogroup"
        :aria-label="prompt"
      >
        <label
          v-for="option in displayOptions"
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
      <div
        v-if="otherSelected"
        class="agent-block__question-other"
      >
        <label class="agent-block__question-other-label" :for="`${radioGroupName}-other`">
          Your answer
        </label>
        <textarea
          :id="`${radioGroupName}-other`"
          v-model="otherText"
          class="agent-block__question-other-input"
          rows="3"
          placeholder="Type a different answer…"
          :disabled="live || submitting"
          @keydown.enter.exact.prevent="continueWithSelection"
        />
      </div>
      <div class="agent-block__question-actions">
        <button
          type="button"
          class="agent-block__question-continue"
          :disabled="!canContinue"
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
