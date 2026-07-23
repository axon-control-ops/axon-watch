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
  kairoVoiceLastPreview,
} from '../../lib/kairo-voice-diagnostics';
import { fetchKairoVoiceLog, type KairoVoiceLogEntry } from '../../lib/kairo-voice-log-client';
import { isKairoVoiceSpeaking, subscribeKairoVoiceSpeaking } from '../../lib/kairo-voice-playback';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const speaking = ref(false);
const voiceLog = ref<KairoVoiceLogEntry[]>([]);
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
  return 'Listening via orb';
});

function refreshSpeakingState(): void {
  speaking.value = isKairoVoiceSpeaking();
}

async function refreshVoiceLog(): Promise<void> {
  if (!showDevVoiceDiagnostics) {
    return;
  }
  try {
    voiceLog.value = await fetchKairoVoiceLog(5);
  } catch {
    voiceLog.value = [];
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
      <span class="kairo-voice-deck__presence-pill" :data-state="presenceState">
        {{ presenceLabel }}
      </span>
    </header>

    <div class="kairo-voice-deck__body kairo-voice-deck__body--text">
      <div class="kairo-voice-deck__copy">
        <p class="kairo-voice-deck__line">{{ statusLine }}</p>
        <template v-if="!shell.operatorBrainGalaxyActive">
          <p v-if="notice" class="kairo-voice-deck__notice">{{ notice }}</p>
          <p v-if="advise" class="kairo-voice-deck__advise">{{ advise }}</p>
          <p class="kairo-voice-deck__hint">
            Use the floating orb to talk · this card is status only
          </p>
          <div v-if="showDevVoiceDiagnostics" class="kairo-voice-deck__dev-diagnostics">
            <p class="kairo-voice-deck__dev-line">{{ kairoVoiceDiagnosticsLabel() }}</p>
            <p v-if="kairoVoiceLastPreview" class="kairo-voice-deck__dev-line">
              Last: {{ kairoVoiceLastPreview }}
            </p>
            <ul v-if="voiceLog.length" class="kairo-voice-deck__dev-log">
              <li v-for="entry in voiceLog" :key="entry.entry_id">
                <span>{{ entry.normalized_content }}</span>
                <span> → {{ entry.reply }}</span>
              </li>
            </ul>
          </div>
        </template>
      </div>
    </div>

    <div class="kairo-voice-deck__actions">
      <button
        type="button"
        class="kairo-voice-deck__action kairo-voice-deck__action--primary"
        :disabled="voiceBlocked"
        @click="shell.speakOperatorBriefing().then(() => refreshVoiceLog())"
      >
        Speak briefing
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
