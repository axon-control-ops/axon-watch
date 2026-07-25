<script setup lang="ts">
import { computed, ref } from 'vue';

import { OPERATOR_PERSONA_NAME } from '../../lib/operator-persona-name';
import { useKairoConversation } from '../../features/kairo-conversation/use-kairo-conversation';
import {
  VAXON_AVATAR_ALT,
  resolveVaxonAvatarFallbackUrl,
  resolveVaxonAvatarUrl,
} from '../../lib/vaxon-avatar-view';
import { useShellStore } from '../../stores/shell';

const props = defineProps<{
  speaking: boolean;
  line: string;
  remainingSeconds: number;
  onDismiss?: () => void;
  onReplied?: () => void;
}>();

const shell = useShellStore();
const { pending, submitTurn } = useKairoConversation();
const reply = ref('');
const avatarSrc = ref(resolveVaxonAvatarUrl());
const asksForReply = computed(() =>
  /\b(shall i|would you like me to|do you want me to)\b/i.test(props.line),
);

function onAvatarError(): void {
  avatarSrc.value = resolveVaxonAvatarFallbackUrl();
}

async function send(content?: string): Promise<void> {
  const message = (content ?? reply.value).trim();
  if (!message || pending.value) {
    return;
  }
  reply.value = '';
  props.onReplied?.();
  await submitTurn(message);
}

function openBriefing(): void {
  shell.focusKairoBriefing();
}

function dismiss(): void {
  props.onDismiss?.();
}
</script>

<template>
  <article
    class="vaxon-roster-voice-dock"
    :data-speaking="speaking ? 'true' : 'false'"
    aria-label="Reply to VAXON"
  >
    <header class="vaxon-roster-voice-dock__header">
      <div class="vaxon-roster-voice-dock__avatar-wrap" aria-hidden="true">
        <img
          class="vaxon-roster-voice-dock__avatar"
          :src="avatarSrc"
          :alt="VAXON_AVATAR_ALT"
          width="48"
          height="48"
          @error="onAvatarError"
        >
        <span class="vaxon-roster-voice-dock__orb-ring" />
      </div>
      <div>
        <p class="vaxon-roster-voice-dock__eyebrow">
          {{
            speaking
              ? 'VAXON · speaking'
              : remainingSeconds > 0
                ? `VAXON · reply window · ${remainingSeconds}s`
                : 'VAXON · briefing'
          }}
        </p>
        <h4 class="vaxon-roster-voice-dock__title">
          {{ speaking ? 'Briefing you now' : 'Your response' }}
        </h4>
      </div>
    </header>

    <p v-if="line" class="vaxon-roster-voice-dock__line">{{ line }}</p>

    <div class="vaxon-roster-voice-dock__quick-actions">
      <button type="button" :disabled="pending" @click="openBriefing">
        Open briefing
      </button>
      <button type="button" :disabled="pending" @click="dismiss">
        Dismiss
      </button>
    </div>

    <div v-if="asksForReply" class="vaxon-roster-voice-dock__quick-actions">
      <button type="button" :disabled="pending" @click="void send('yes')">
        Yes — dig in
      </button>
      <button type="button" :disabled="pending" @click="void send('no')">
        Not now
      </button>
    </div>

    <form class="vaxon-roster-voice-dock__form" @submit.prevent="void send()">
      <input
        v-model="reply"
        type="text"
        autocomplete="off"
        :placeholder="`Reply to ${OPERATOR_PERSONA_NAME}…`"
        :disabled="pending"
      >
      <button type="submit" :disabled="pending || !reply.trim()">
        {{ pending ? 'Sending…' : 'Reply' }}
      </button>
    </form>
  </article>
</template>
