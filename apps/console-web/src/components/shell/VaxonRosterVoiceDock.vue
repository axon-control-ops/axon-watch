<script setup lang="ts">
import { computed, ref } from 'vue';

import OperatorPersonaMark from '../OperatorPersonaMark.vue';
import { OPERATOR_PERSONA_NAME } from '../../lib/operator-persona-name';
import { useKairoConversation } from '../../features/kairo-conversation/use-kairo-conversation';

const props = defineProps<{
  speaking: boolean;
  line: string;
  remainingSeconds: number;
}>();

const { pending, submitTurn } = useKairoConversation();
const reply = ref('');
const asksForReply = computed(() =>
  /\b(shall i|would you like me to|do you want me to)\b/i.test(props.line),
);

async function send(content?: string): Promise<void> {
  const message = (content ?? reply.value).trim();
  if (!message || pending.value) {
    return;
  }
  reply.value = '';
  await submitTurn(message);
}
</script>

<template>
  <article
    class="vaxon-roster-voice-dock"
    :data-speaking="speaking ? 'true' : 'false'"
    aria-label="Reply to VAXON"
  >
    <header class="vaxon-roster-voice-dock__header">
      <div class="vaxon-roster-voice-dock__orb" aria-hidden="true">
        <span class="vaxon-roster-voice-dock__orb-ring" />
        <OperatorPersonaMark :size="18" />
      </div>
      <div>
        <p class="vaxon-roster-voice-dock__eyebrow">
          {{ speaking ? 'VAXON · speaking' : `VAXON · reply window · ${remainingSeconds}s` }}
        </p>
        <h4 class="vaxon-roster-voice-dock__title">
          {{ speaking ? 'Briefing you now' : 'Your response' }}
        </h4>
      </div>
    </header>

    <p v-if="line" class="vaxon-roster-voice-dock__line">{{ line }}</p>

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
        {{ pending ? 'Sending…' : 'Send' }}
      </button>
    </form>
  </article>
</template>
