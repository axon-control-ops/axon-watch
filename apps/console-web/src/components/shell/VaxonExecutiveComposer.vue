<script setup lang="ts">
import { computed, nextTick, ref } from 'vue';

import { OPERATOR_PERSONA_NAME } from '../../lib/operator-persona-name';
import {
  buildVaxonComposerSubmission,
  shouldSubmitVaxonComposer,
  type VaxonExecutiveComposerMode,
  vaxonComposerSubmissionIntent,
} from '../../lib/vaxon-executive-composer';

const props = defineProps<{
  pending: boolean;
  micLive: boolean;
  micSupported: boolean;
  focusedWorkspaceLabel: string | null;
}>();

const emit = defineEmits<{
  submit: [payload: { content: string; submissionIntent: 'ask' | 'dispatch' }];
  toggleMic: [];
}>();

const draft = ref('');
// Conversation is the safe default. Dispatching work is a deliberate choice
// made after VAXON and the operator have agreed the mission.
const mode = ref<VaxonExecutiveComposerMode>('ask');
const expanded = ref(false);
const composerInput = ref<HTMLTextAreaElement | null>(null);

const placeholder = computed(() =>
  mode.value === 'mission'
    ? 'State the objective, success criteria, constraints, or deliverables…'
    : `Ask ${OPERATOR_PERSONA_NAME} for analysis, status, or a recommendation…`,
);

const submitLabel = computed(() =>
  mode.value === 'mission' ? 'Dispatch mission' : `Ask ${OPERATOR_PERSONA_NAME}`,
);

function submit(content?: string, modeValue = mode.value): void {
  const raw = (content ?? draft.value).trim();
  if (!raw || props.pending) {
    return;
  }
  const message = content === undefined ? buildVaxonComposerSubmission(raw, modeValue) : raw;
  draft.value = '';
  expanded.value = false;
  emit('submit', {
    content: message,
    submissionIntent: vaxonComposerSubmissionIntent(modeValue),
  });
}

function selectMode(nextMode: VaxonExecutiveComposerMode): void {
  mode.value = nextMode;
  void nextTick(() => composerInput.value?.focus());
}

async function toggleExpanded(): Promise<void> {
  expanded.value = !expanded.value;
  await nextTick();
  composerInput.value?.focus();
}

function handleKeydown(event: KeyboardEvent): void {
  if (shouldSubmitVaxonComposer(event) && draft.value.trim() && !props.pending) {
    event.preventDefault();
    submit();
  }
}
</script>

<template>
  <div class="mc-live-ops__reply" :class="{ 'mc-live-ops__reply--expanded': expanded }">
    <form class="mc-live-ops__reply-form" @submit.prevent="submit()">
      <div class="mc-exec-composer__input-row">
        <span class="mc-exec-composer__mark" aria-hidden="true">V</span>
        <textarea
          ref="composerInput"
          v-model="draft"
          :rows="expanded ? 3 : 1"
          autocomplete="off"
          :placeholder="placeholder"
          :disabled="pending"
          :aria-label="`${OPERATOR_PERSONA_NAME} mission or question input`"
          @keydown="handleKeydown"
        />
        <button
          type="button"
          class="mc-live-ops__mic"
          :data-live="micLive ? 'true' : 'false'"
          :disabled="!micSupported || pending"
          :title="micLive ? 'Stop listening' : 'Speak executive intent'"
          :aria-pressed="micLive"
          @click="emit('toggleMic')"
        >
          <span aria-hidden="true">{{ micLive ? '●' : '◌' }}</span>
          <span class="mc-exec-composer__sr-only">{{ micLive ? 'Stop listening' : 'Speak executive intent' }}</span>
        </button>
        <button type="submit" class="mc-live-ops__send" :disabled="pending || !draft.trim()">
          <span class="mc-exec-composer__send-label">{{ pending ? 'Working…' : submitLabel }}</span>
          <span class="mc-exec-composer__send-icon" aria-hidden="true">↗</span>
        </button>
      </div>
    </form>

    <footer class="mc-exec-composer__context" aria-label="Mission composer context">
      <div class="mc-exec-composer__modes" role="group" aria-label="Submission mode">
        <button
          type="button"
          class="mc-exec-composer__mode"
          :data-active="mode === 'ask' ? 'true' : 'false'"
          :disabled="pending"
          title="Ask VAXON for information only; this cannot dispatch work"
          @click="selectMode('ask')"
        >
          Ask
        </button>
        <button
          type="button"
          class="mc-exec-composer__mode"
          :data-active="mode === 'mission' ? 'true' : 'false'"
          :disabled="pending"
          title="Dispatch a mission for specialist routing"
          @click="selectMode('mission')"
        >
          Mission
        </button>
      </div>
      <span class="mc-exec-composer__context-copy">
        {{ focusedWorkspaceLabel || 'Fleet' }}
        <span aria-hidden="true">·</span>
        {{ expanded ? 'Shift+Enter for a new line' : 'Enter to send' }}
      </span>
      <button
        type="button"
        class="mc-exec-composer__expand"
        :aria-expanded="expanded"
        :disabled="pending"
        @click="void toggleExpanded()"
      >
        {{ expanded ? 'Compact' : 'Details' }}
      </button>
      <button
        v-if="expanded"
        type="button"
        class="mc-exec-composer__brief"
        :disabled="pending"
        @click="submit('REPORT', 'ask')"
      >
        Brief
      </button>
    </footer>
  </div>
</template>

<style scoped src="./mission-control-executive-composer.css"></style>
