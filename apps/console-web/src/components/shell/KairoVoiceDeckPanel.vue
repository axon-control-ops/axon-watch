<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

import {
  voiceCockpitPresenceState,
  voiceCockpitStatusLine,
} from '../../features/voice-deck/voice-cockpit-presence';
import { briefingNotice, briefingAdvise } from '../../lib/briefing-panel-view';
import PersonaTitle from '../../components/PersonaTitle.vue';
import {
  kairoVoiceDiagnosticsLabel,
  kairoVoiceLastEngine,
  kairoVoiceLastPreview,
  kairoVoiceLastReason,
} from '../../lib/kairo-voice-diagnostics';
import { fetchKairoVoiceLog, type KairoVoiceLogEntry } from '../../lib/kairo-voice-log-client';
import { isKairoVoiceSpeaking, subscribeKairoVoiceSpeaking } from '../../lib/kairo-voice-playback';
import { deliverSpokenOperatorAlert } from '../../lib/spoken-alert-delivery';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const speaking = ref(false);
const speakingBriefing = ref(false);
const voiceLog = ref<KairoVoiceLogEntry[]>([]);
const voiceDraft = ref('');
const speakingDraft = ref(false);
let unsubscribeSpeaking: (() => void) | null = null;
const showDevVoiceDiagnostics = import.meta.env.DEV;

const presence = computed(() => shell.operatorBriefing?.operator_presence ?? null);
const presenceState = computed(() => voiceCockpitPresenceState(presence.value));
const statusLine = computed(() => voiceCockpitStatusLine(presence.value));
const notice = computed(() =>
  briefingNotice(shell.operatorBriefing, shell.briefingLoadState),
);
const advise = computed(() =>
  briefingAdvise(shell.operatorBriefing, shell.briefingLoadState),
);

const voiceBlocked = computed(
  () =>
    shell.operatorPresenceSettings.privacy_mode ||
    shell.operatorPresenceSettings.kairo_narration === 'off' ||
    !shell.operatorPresenceSettings.spoken_alerts_enabled,
);

const presenceLabel = computed(() => {
  if (voiceBlocked.value) {
    return 'Standby';
  }
  if (speaking.value) {
    return 'Speaking';
  }
  if (presenceState.value === 'alerting') {
    return 'Alert';
  }
  return 'Ready';
});

const diagnosticsLabel = computed(() => {
  void kairoVoiceLastEngine.value;
  void kairoVoiceLastReason.value;
  return kairoVoiceDiagnosticsLabel();
});

function refreshSpeakingState(): void {
  speaking.value = isKairoVoiceSpeaking();
}

async function refreshVoiceLog(): Promise<void> {
  if (!showDevVoiceDiagnostics) {
    return;
  }
  try {
    voiceLog.value = await fetchKairoVoiceLog(12);
  } catch {
    voiceLog.value = [];
  }
}

async function onSpeakBriefing(): Promise<void> {
  if (speakingBriefing.value || voiceBlocked.value) {
    return;
  }
  speakingBriefing.value = true;
  try {
    await shell.speakOperatorBriefing();
    await refreshVoiceLog();
  } finally {
    speakingBriefing.value = false;
  }
}

async function speakVoiceDraft(): Promise<void> {
  const message = voiceDraft.value.trim();
  if (!message || voiceBlocked.value || speakingDraft.value) {
    return;
  }
  speakingDraft.value = true;
  try {
    await deliverSpokenOperatorAlert(
      {
        eligible: true,
        reason: 'operator_voice_deck_draft',
        signal_id: null,
        message,
      },
      sessionStorage,
      { dedupe: false },
    );
    await refreshVoiceLog();
  } finally {
    speakingDraft.value = false;
  }
}

function onVoiceDraftKeydown(event: KeyboardEvent): void {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    void speakVoiceDraft();
  }
}

onMounted(() => {
  refreshSpeakingState();
  unsubscribeSpeaking = subscribeKairoVoiceSpeaking((active) => {
    speaking.value = active;
  });
  void refreshVoiceLog();
});

onBeforeUnmount(() => {
  unsubscribeSpeaking?.();
});
</script>

<template>
  <section
    class="kairo-voice-deck hud-panel-frame kairo-voice-deck--text-only"
    :class="[
      `kairo-voice-deck--${presenceState}`,
      { 'kairo-voice-deck--speaking': speaking },
      { 'kairo-voice-deck--galaxy-compact': shell.operatorBrainGalaxyActive },
    ]"
    aria-label="Operator voice control"
  >
    <header class="kairo-voice-deck__head">
      <p class="kairo-voice-deck__title">
        <PersonaTitle suffix="Voice" mark-size="xs" />
      </p>
      <span
        v-if="presenceLabel !== 'Ready'"
        class="kairo-voice-deck__presence-pill"
        :data-state="presenceState"
      >
        {{ presenceLabel }}
      </span>
    </header>

    <div class="kairo-voice-deck__body kairo-voice-deck__body--text">
      <div class="kairo-voice-deck__copy">
        <p class="kairo-voice-deck__line">{{ statusLine }}</p>
        <template v-if="!shell.operatorBrainGalaxyActive">
          <p v-if="notice" class="kairo-voice-deck__notice">{{ notice }}</p>
          <p v-if="advise" class="kairo-voice-deck__advise">{{ advise }}</p>
          <div v-if="showDevVoiceDiagnostics" class="kairo-voice-deck__dev-diagnostics">
            <p class="kairo-voice-deck__dev-line">{{ diagnosticsLabel }}</p>
            <p v-if="kairoVoiceLastPreview" class="kairo-voice-deck__dev-line">
              Last: {{ kairoVoiceLastPreview }}
            </p>
            <ul v-if="voiceLog.length" class="kairo-voice-deck__dev-log">
              <li v-for="entry in voiceLog" :key="entry.entry_id">
                <span>{{ entry.normalized_content }}</span>
                <span> → {{ entry.reply }}</span>
              </li>
            </ul>
            <label class="kairo-voice-deck__draft">
              <textarea
                v-model="voiceDraft"
                class="kairo-voice-deck__draft-input"
                rows="2"
                placeholder="Type a voice line…"
                aria-label="Voice line"
                :disabled="voiceBlocked || speakingDraft"
                @keydown="onVoiceDraftKeydown"
              />
            </label>
          </div>
        </template>
      </div>
    </div>

    <div class="kairo-voice-deck__actions">
      <button
        type="button"
        class="kairo-voice-deck__action kairo-voice-deck__action--primary"
        :disabled="voiceBlocked || speakingBriefing"
        :aria-busy="speakingBriefing"
        @click="onSpeakBriefing"
      >
        {{ speakingBriefing ? 'Speaking…' : 'Speak briefing' }}
      </button>
      <button
        v-if="!shell.operatorBrainGalaxyActive"
        type="button"
        class="kairo-voice-deck__action"
        @click="shell.focusKairoBriefing()"
      >
        Open briefing
      </button>
    </div>
  </section>
</template>
