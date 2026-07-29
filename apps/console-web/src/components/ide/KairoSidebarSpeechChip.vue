<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';

import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import { useKairoConversation } from '../../features/kairo-conversation/use-kairo-conversation';
import type { KairoVoiceSpeaker } from '../../lib/kairo-voice-utterance';
import { OPERATOR_PERSONA_NAME } from '../../lib/operator-persona-name';
import { runEmployeeShiftRetry } from '../../lib/run-employee-shift-retry';
import {
  resolveSidebarSpeechReplyTarget,
} from '../../lib/sidebar-speech-reply-route';
import {
  resolveSidebarSpeechChipView,
  sidebarSpeechCanExpand,
} from '../../lib/sidebar-speech-chip-view';
import { vaxonAffirmReplyCta, vaxonLineAsksForReply } from '../../lib/vaxon-reply-prompt';
import { useShellStore } from '../../stores/shell';

const props = defineProps<{
  spokenText: string | null;
  speaker: KairoVoiceSpeaker | null;
  speaking: boolean;
  fallbackPersonaName: string;
  stickyText?: string;
  stickySpeakerName?: string;
  stickySpeakerKind?: 'vaxon' | 'employee' | null;
  stickySpeakerId?: string | null;
  showDismiss?: boolean;
  /** Show text/voice reply controls so the operator can continue the flow. */
  awaitingReply?: boolean;
  employees?: CompanyEmployeeRecord[];
}>();

const emit = defineEmits<{
  stopSpeech: [];
  dismiss: [];
  replied: [];
}>();

const shell = useShellStore();
const localStickyText = ref('');
const localStickySpeakerName = ref('');
const expanded = ref(false);
const reply = ref('');
const replyInputRef = ref<HTMLInputElement | null>(null);
const { pending, submitTurn } = useKairoConversation();
const sending = ref(false);

watch(
  () =>
    [
      props.spokenText,
      props.speaker?.name,
      props.fallbackPersonaName,
      props.stickyText,
      props.stickySpeakerName,
    ] as const,
  ([text, name, fallback, parentSticky, parentSpeaker]) => {
    const next = text?.trim() ?? '';
    if (next) {
      localStickyText.value = next;
      localStickySpeakerName.value = name?.trim() || fallback.trim() || 'Agent';
      return;
    }
    if (parentSticky?.trim()) {
      localStickyText.value = parentSticky.trim();
      localStickySpeakerName.value =
        parentSpeaker?.trim() || fallback.trim() || localStickySpeakerName.value || 'Agent';
    }
  },
  { immediate: true },
);

const view = computed(() =>
  resolveSidebarSpeechChipView({
    spokenText: props.spokenText,
    speaker: props.speaker,
    speaking: props.speaking,
    fallbackPersonaName: props.fallbackPersonaName,
    stickyText: props.stickyText?.trim() || localStickyText.value,
    stickySpeakerName: props.stickySpeakerName?.trim() || localStickySpeakerName.value,
  }),
);
const canExpand = computed(() => sidebarSpeechCanExpand(view.value.displayText));
const showReplyBlock = computed(
  () => Boolean(props.awaitingReply) && !view.value.empty,
);
const asksForQuickReply = computed(() => vaxonLineAsksForReply(view.value.displayText));
const affirmCta = computed(() => vaxonAffirmReplyCta(view.value.displayText));
const replyTarget = computed(() =>
  resolveSidebarSpeechReplyTarget({
    line: view.value.displayText,
    speakerKind: props.speaker?.kind ?? props.stickySpeakerKind,
    speakerId: props.speaker?.id ?? props.stickySpeakerId,
    speakerName: props.speaker?.name ?? props.stickySpeakerName ?? view.value.stickySpeakerName,
    vaxonName: OPERATOR_PERSONA_NAME,
    employees: props.employees ?? [],
  }),
);
const replyTargetName = computed(() =>
  replyTarget.value.kind === 'employee'
    ? replyTarget.value.employee.name.trim() || 'teammate'
    : OPERATOR_PERSONA_NAME,
);
const busy = computed(() => pending.value || sending.value);

watch(
  () => view.value.displayText,
  () => {
    expanded.value = false;
  },
);

watch(
  showReplyBlock,
  async (active) => {
    if (!active) {
      return;
    }
    await nextTick();
    replyInputRef.value?.focus();
  },
);

function toggleExpanded(): void {
  expanded.value = !expanded.value;
}

async function send(content?: string): Promise<void> {
  const message = (content ?? reply.value).trim();
  if (!message || busy.value) {
    return;
  }
  reply.value = '';
  sending.value = true;
  try {
    const target = resolveSidebarSpeechReplyTarget({
      line: view.value.displayText,
      speakerKind: props.speaker?.kind ?? props.stickySpeakerKind,
      speakerId: props.speaker?.id ?? props.stickySpeakerId,
      speakerName: props.speaker?.name ?? props.stickySpeakerName ?? view.value.stickySpeakerName,
      vaxonName: OPERATOR_PERSONA_NAME,
      employees: props.employees ?? [],
      message,
    });
    if (target.kind === 'employee' && target.retry) {
      await runEmployeeShiftRetry(shell, target.employee, {
        keepActivityView: true,
        focusThread: true,
      });
      emit('replied');
      return;
    }
    if (target.kind === 'employee') {
      await shell.openOrFocusEmployeeIdeThread?.(target.employee);
      shell.setAgentExecutionAccess('full');
      shell.openIdeComposerWithDraft(message, { keepActivityView: true });
      await shell.submitIdeComposer('agent');
      emit('replied');
      return;
    }
    emit('replied');
    await submitTurn(message);
  } finally {
    sending.value = false;
  }
}
</script>

<template>
  <section
    class="kairo-sidebar-speech"
    :class="{
      'kairo-sidebar-speech--expanded': expanded || showReplyBlock,
      'kairo-sidebar-speech--awaiting-reply': showReplyBlock,
    }"
    :data-speaking="speaking ? 'true' : 'false'"
    :aria-label="view.statusLabel"
    @click.stop
  >
    <header class="kairo-sidebar-speech__header">
      <span class="kairo-sidebar-speech__identity">
        <span class="kairo-sidebar-speech__activity" aria-hidden="true">
          <span />
          <span />
          <span />
        </span>
        <span class="kairo-sidebar-speech__label">{{ view.statusLabel }}</span>
      </span>
      <span class="kairo-sidebar-speech__actions">
        <button
          v-if="canExpand && !showReplyBlock"
          type="button"
          class="kairo-sidebar-speech__expand"
          :aria-expanded="expanded"
          @click="toggleExpanded"
        >
          {{ expanded ? 'Less' : 'More' }}
        </button>
        <button
          v-if="speaking"
          type="button"
          class="kairo-sidebar-speech__stop"
          @click="emit('stopSpeech')"
        >
          Stop
        </button>
        <button
          v-else-if="showDismiss"
          type="button"
          class="kairo-sidebar-speech__dismiss"
          @click="emit('dismiss')"
        >
          Dismiss
        </button>
      </span>
    </header>

    <div class="kairo-sidebar-speech__body">
      <p v-if="!view.empty" class="kairo-sidebar-speech__text">
        {{ view.displayText }}
      </p>
      <p v-else class="kairo-sidebar-speech__empty">
        Spoken replies from the agent who is talking appear here.
      </p>
    </div>

    <div v-if="showReplyBlock" class="kairo-sidebar-speech__reply" @click.stop>
      <p class="kairo-sidebar-speech__reply-hint">
        Reply to {{ replyTargetName }} — text or voice
      </p>
      <div v-if="asksForQuickReply" class="kairo-sidebar-speech__reply-actions">
        <button type="button" :disabled="busy" @click="void send(affirmCta === 'Try again' ? 'Try again' : 'yes')">
          {{ affirmCta }}
        </button>
        <button type="button" :disabled="busy" @click="void send('no')">
          Not now
        </button>
      </div>
      <form class="kairo-sidebar-speech__reply-form" @submit.prevent="void send()">
        <input
          ref="replyInputRef"
          v-model="reply"
          type="text"
          autocomplete="off"
          :placeholder="`Reply to ${replyTargetName}…`"
          :disabled="busy"
          :aria-label="`Reply to ${replyTargetName}`"
        >
        <button type="submit" :disabled="busy || !reply.trim()">
          {{ busy ? 'Sending…' : 'Reply' }}
        </button>
      </form>
    </div>
  </section>
</template>
