<script setup lang="ts">
import { computed, ref, useId, watch } from 'vue';

import {
  AGENT_QUESTION_OTHER_ID,
  AGENT_QUESTION_PROMPT_MAX,
  formatAnsweredQuestionChoice,
  isAgentQuestionOtherOption,
  moveQuestionOptionSelection,
  truncateQuestionOptionLabel,
  truncateQuestionPrompt,
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
  /** Stable per-segment id so multiple asks in one message stay isolated. */
  segmentIndex?: number;
  /** When set, render Cursor-like collapsed answered card. */
  answeredOption?: AgentQuestionOption | null;
}>();

const shell = useShellStore();
const instanceId = useId();
const displayOptions = computed(() => withOtherQuestionOption(props.options));
const selectionStorageKey = computed(
  () =>
    `axon-agent-question-selection:${props.messageId || 'local'}:${props.segmentIndex ?? 0}`,
);

function readStoredSelection(): string {
  if (typeof sessionStorage === 'undefined') {
    return '';
  }
  try {
    return sessionStorage.getItem(selectionStorageKey.value)?.trim() || '';
  } catch {
    return '';
  }
}

function persistSelection(optionId: string): void {
  if (typeof sessionStorage === 'undefined' || !optionId) {
    return;
  }
  try {
    sessionStorage.setItem(selectionStorageKey.value, optionId);
  } catch {
    /* ignore quota / private mode */
  }
}

const storedSelection = readStoredSelection();
const selectedId = ref(
  props.answeredOption?.id ||
    (storedSelection &&
    withOtherQuestionOption(props.options).some((option) => option.id === storedSelection)
      ? storedSelection
      : '') ||
    displayOptions.value[0]?.id ||
    '',
);
const operatorTouchedSelection = ref(Boolean(storedSelection));
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

const groupLabelId = computed(
  () => `axon-agent-question-label-${instanceId}-${props.messageId || 'local'}-${props.segmentIndex ?? 0}`,
);

const promptExpanded = ref(false);
const normalizedPrompt = computed(() => props.prompt.trim());
const promptNeedsExpand = computed(() => normalizedPrompt.value.length > AGENT_QUESTION_PROMPT_MAX);
const displayPrompt = computed(() => {
  if (promptExpanded.value || !promptNeedsExpand.value) {
    return normalizedPrompt.value;
  }
  return truncateQuestionPrompt(normalizedPrompt.value);
});
const answeredChoiceLabel = computed(() =>
  resolvedAnswer.value ? formatAnsweredQuestionChoice(resolvedAnswer.value) : '',
);

function optionDisplayLabel(option: AgentQuestionOption): string {
  return truncateQuestionOptionLabel(option.label);
}

watch(
  () => props.options,
  () => {
    if (displayOptions.value.some((option) => option.id === selectedId.value)) {
      return;
    }
    if (operatorTouchedSelection.value) {
      // Keep the operator's pick even if a live refresh briefly reshuffles ids;
      // only fall back when the selected id truly disappeared.
      const stored = readStoredSelection();
      if (stored && displayOptions.value.some((option) => option.id === stored)) {
        selectedId.value = stored;
        return;
      }
    }
    selectedId.value = displayOptions.value[0]?.id || '';
  },
);

watch(
  () => props.answeredOption?.id,
  (answeredId) => {
    if (answeredId && !locallyAnswered.value) {
      selectedId.value = answeredId;
    }
  },
);

function selectOption(optionId: string): void {
  if (props.live || submitting.value || isAnswered.value) {
    return;
  }
  selectedId.value = optionId;
  operatorTouchedSelection.value = true;
  persistSelection(optionId);
}

function optionButtonId(optionId: string): string {
  return `${instanceId}-option-${optionId}`;
}

function focusOptionButton(optionId: string): void {
  document.getElementById(optionButtonId(optionId))?.focus();
}

function handleOptionKeydown(event: KeyboardEvent, optionId: string): void {
  if (props.live || submitting.value || isAnswered.value) {
    return;
  }

  if (event.key === 'ArrowDown' || event.key === 'ArrowRight') {
    event.preventDefault();
    const nextId = moveQuestionOptionSelection(displayOptions.value, selectedId.value, 'next');
    selectOption(nextId);
    focusOptionButton(nextId);
    return;
  }

  if (event.key === 'ArrowUp' || event.key === 'ArrowLeft') {
    event.preventDefault();
    const prevId = moveQuestionOptionSelection(displayOptions.value, selectedId.value, 'prev');
    selectOption(prevId);
    focusOptionButton(prevId);
    return;
  }

  if (event.key === 'Enter' && optionId === selectedId.value && !otherSelected.value) {
    event.preventDefault();
    void continueWithSelection();
  }
}

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
    :aria-labelledby="groupLabelId"
  >
    <template v-if="isAnswered && resolvedAnswer">
      <p class="agent-block__question-kicker">Answered</p>
      <p
        :id="groupLabelId"
        class="agent-block__question-prompt"
      >
        {{ displayPrompt }}
      </p>
      <button
        v-if="promptNeedsExpand"
        type="button"
        class="agent-block__question-expand"
        @click="promptExpanded = !promptExpanded"
      >
        {{ promptExpanded ? 'Show less' : 'Show full question' }}
      </button>
      <p
        class="agent-block__question-answered-choice"
        :title="resolvedAnswer.label"
      >
        {{ answeredChoiceLabel }}
      </p>
    </template>
    <template v-else>
      <p class="agent-block__question-kicker">Question</p>
      <p
        :id="groupLabelId"
        class="agent-block__question-prompt"
      >
        {{ displayPrompt }}
      </p>
      <button
        v-if="promptNeedsExpand"
        type="button"
        class="agent-block__question-expand"
        @click="promptExpanded = !promptExpanded"
      >
        {{ promptExpanded ? 'Show less' : 'Show full question' }}
      </button>
      <div
        class="agent-block__question-options"
        role="radiogroup"
        :aria-labelledby="groupLabelId"
      >
        <button
          v-for="option in displayOptions"
          :id="optionButtonId(option.id)"
          :key="`${instanceId}-${option.id}`"
          type="button"
          class="agent-block__question-option"
          :class="{ 'agent-block__question-option--selected': selectedId === option.id }"
          role="radio"
          :aria-checked="selectedId === option.id"
          :disabled="live || submitting"
          :tabindex="selectedId === option.id ? 0 : -1"
          @click="selectOption(option.id)"
          @keydown="handleOptionKeydown($event, option.id)"
        >
          <span
            class="agent-block__question-radio"
            aria-hidden="true"
          />
          <span
            v-if="!isAgentQuestionOtherOption(option)"
            class="agent-block__question-id"
          >{{ option.id }}</span>
          <span
            v-else
            class="agent-block__question-id"
            aria-hidden="true"
          />
          <span
            class="agent-block__question-label"
            :title="option.label"
          >
            {{ optionDisplayLabel(option) }}
          </span>
        </button>
      </div>
      <div
        v-if="otherSelected"
        class="agent-block__question-other"
      >
        <label
          class="agent-block__question-other-label"
          :for="`${instanceId}-other`"
        >
          Your answer
        </label>
        <textarea
          :id="`${instanceId}-other`"
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
