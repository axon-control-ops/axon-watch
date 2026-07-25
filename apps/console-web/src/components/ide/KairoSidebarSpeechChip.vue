<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import type { KairoVoiceSpeaker } from '../../lib/kairo-voice-utterance';
import { resolveSidebarSpeechChipView } from '../../lib/sidebar-speech-chip-view';

const props = defineProps<{
  spokenText: string | null;
  speaker: KairoVoiceSpeaker | null;
  speaking: boolean;
  fallbackPersonaName: string;
}>();

const emit = defineEmits<{
  stopSpeech: [];
}>();

const stickyText = ref('');
const stickySpeakerName = ref('');

watch(
  () => [props.spokenText, props.speaker?.name, props.fallbackPersonaName] as const,
  ([text, name, fallback]) => {
    const next = text?.trim() ?? '';
    if (!next) {
      return;
    }
    stickyText.value = next;
    stickySpeakerName.value = name?.trim() || fallback.trim() || 'Agent';
  },
  { immediate: true },
);

const view = computed(() =>
  resolveSidebarSpeechChipView({
    spokenText: props.spokenText,
    speaker: props.speaker,
    speaking: props.speaking,
    fallbackPersonaName: props.fallbackPersonaName,
    stickyText: stickyText.value,
    stickySpeakerName: stickySpeakerName.value,
  }),
);
</script>

<template>
  <section
    class="kairo-sidebar-speech"
    :data-speaking="speaking ? 'true' : 'false'"
    :aria-label="view.statusLabel"
    @click.stop
  >
    <header class="kairo-sidebar-speech__header">
      <span class="kairo-sidebar-speech__label">{{ view.statusLabel }}</span>
      <button
        v-if="speaking"
        type="button"
        class="kairo-sidebar-speech__stop"
        @click="emit('stopSpeech')"
      >
        Stop
      </button>
    </header>

    <div class="kairo-sidebar-speech__body">
      <p v-if="!view.empty" class="kairo-sidebar-speech__text">
        {{ view.displayText }}
      </p>
      <p v-else class="kairo-sidebar-speech__empty">
        Spoken replies from the agent who is talking appear here.
      </p>
    </div>
  </section>
</template>
