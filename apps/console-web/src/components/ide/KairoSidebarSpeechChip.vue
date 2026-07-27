<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import type { KairoVoiceSpeaker } from '../../lib/kairo-voice-utterance';
import {
  resolveSidebarSpeechChipView,
  sidebarSpeechCanExpand,
} from '../../lib/sidebar-speech-chip-view';

const props = defineProps<{
  spokenText: string | null;
  speaker: KairoVoiceSpeaker | null;
  speaking: boolean;
  fallbackPersonaName: string;
  stickyText?: string;
  stickySpeakerName?: string;
  showDismiss?: boolean;
}>();

const emit = defineEmits<{
  stopSpeech: [];
  dismiss: [];
}>();

const localStickyText = ref('');
const localStickySpeakerName = ref('');
const expanded = ref(false);

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

watch(
  () => view.value.displayText,
  () => {
    expanded.value = false;
  },
);

function toggleExpanded(): void {
  expanded.value = !expanded.value;
}
</script>

<template>
  <section
    class="kairo-sidebar-speech"
    :class="{ 'kairo-sidebar-speech--expanded': expanded }"
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
          v-if="canExpand"
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
  </section>
</template>
