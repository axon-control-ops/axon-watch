<script setup lang="ts">
import { computed, ref } from 'vue';

import { OPERATOR_PERSONA_NAME } from '../../lib/operator-persona-name';
import { useKairoConversation } from '../../features/kairo-conversation/use-kairo-conversation';
import {
  VAXON_AVATAR_ALT,
  resolveVaxonAvatarFallbackUrl,
  resolveVaxonAvatarUrl,
} from '../../lib/vaxon-avatar-view';
import { vaxonAffirmReplyCta, vaxonLineAsksForReply } from '../../lib/vaxon-reply-prompt';
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
const asksForReply = computed(() => vaxonLineAsksForReply(props.line));
const affirmCta = computed(() => vaxonAffirmReplyCta(props.line));

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
    aria-label="VAXON voice and report panel"
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
      <div class="vaxon-roster-voice-dock__heading">
        <p class="vaxon-roster-voice-dock__eyebrow">
          {{
            speaking
              ? 'VAXON · speaking'
              : remainingSeconds > 0
                ? `VAXON · reply window · ${remainingSeconds}s`
                : 'VAXON · report ready'
          }}
        </p>
        <h4 class="vaxon-roster-voice-dock__title">
          {{ speaking ? 'Live voice briefing' : 'VAXON report channel' }}
        </h4>
      </div>
      <span class="vaxon-roster-voice-dock__status-pill">
        {{ pending ? 'Sending' : speaking ? 'Live' : remainingSeconds > 0 ? 'Reply' : 'Ready' }}
      </span>
    </header>

    <section v-if="line" class="vaxon-roster-voice-dock__transcript" aria-label="Latest VAXON message">
      <p class="vaxon-roster-voice-dock__transcript-label">Latest signal</p>
      <p class="vaxon-roster-voice-dock__line">{{ line }}</p>
    </section>

    <div class="vaxon-roster-voice-dock__quick-actions vaxon-roster-voice-dock__quick-actions--primary">
      <button type="button" class="vaxon-roster-voice-dock__primary-action" :disabled="pending" @click="openBriefing">
        Open VAXON report
      </button>
      <button type="button" :disabled="pending" @click="dismiss">
        Dismiss
      </button>
    </div>

    <div v-if="asksForReply" class="vaxon-roster-voice-dock__quick-actions">
      <button type="button" :disabled="pending" @click="void send('yes')">
        {{ affirmCta }}
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
