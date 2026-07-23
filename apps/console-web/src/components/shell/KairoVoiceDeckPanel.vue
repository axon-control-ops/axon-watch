<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

import {
  voiceCockpitPresenceState,
  voiceCockpitStatusLine,
} from '../../features/voice-deck/voice-cockpit-presence';
import { useKairoSpeechCapture } from '../../features/kairo-conversation/use-kairo-speech-capture';
import { kairoConversationPhase } from '../../features/kairo-conversation/kairo-conversation-state';
import {
  kairoAudioUnlockSnapshot,
  unlockKairoAudioPlayback,
} from '../../lib/kairo-audio-unlock';
import { briefingNotice, briefingAdvise } from '../../lib/briefing-panel-view';
import PersonaTitle from '../../components/PersonaTitle.vue';
import {
  kairoVoiceDiagnosticsLabel,
  kairoVoiceLastPreview,
} from '../../lib/kairo-voice-diagnostics';
import { fetchKairoVoiceLog, type KairoVoiceLogEntry } from '../../lib/kairo-voice-log-client';
import { isKairoVoiceSpeaking, subscribeKairoVoiceSpeaking } from '../../lib/kairo-voice-playback';
import { OPERATOR_PERSONA_NAME } from '../../lib/operator-persona-name';
import HudHoloVoiceOrb from '../../features/hud-holo/HudHoloVoiceOrb.vue';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const speaking = ref(false);
const voiceLog = ref<KairoVoiceLogEntry[]>([]);
const voiceDeckRef = ref<HTMLElement | null>(null);
let unsubscribeSpeaking: (() => void) | null = null;
const showDevVoiceDiagnostics = import.meta.env.DEV;

const speechCapture = useKairoSpeechCapture({
  privacyBlocked: () => shell.operatorPresenceSettings.privacy_mode,
  sttMode: () => shell.operatorPresenceSettings.stt_mode,
  stopOnUnmount: 'manual_only',
});

const presence = computed(() => shell.operatorBriefing?.operator_presence ?? null);
const presenceState = computed(() => voiceCockpitPresenceState(presence.value));
const statusLine = computed(() => voiceCockpitStatusLine(presence.value));
const notice = computed(() =>
  briefingNotice(shell.operatorBriefing, shell.briefingLoadState),
);
const advise = computed(() =>
  briefingAdvise(shell.operatorBriefing, shell.briefingLoadState),
);

const needsUnlock = computed(() => !kairoAudioUnlockSnapshot.value.mediaUnlocked);

const micDisabled = computed(
  () =>
    shell.operatorPresenceSettings.privacy_mode ||
    !speechCapture.supported ||
    kairoConversationPhase.value === 'thinking' ||
    shell.kairoSpeechActive,
);

const listening = computed(
  () => speechCapture.capturing.value && speechCapture.captureMode.value === 'manual',
);

const captureError = computed(() => speechCapture.captureError.value);

const liveLine = computed(() => {
  const interim = speechCapture.interimTranscript.value.trim();
  if (interim) {
    return interim;
  }
  if (listening.value) {
    return `Listening — talk to ${OPERATOR_PERSONA_NAME}…`;
  }
  return statusLine.value;
});

const talkHint = computed(() => {
  if (shell.operatorPresenceSettings.privacy_mode) {
    return 'Privacy mode — voice talk is blocked in settings';
  }
  if (!speechCapture.supported) {
    return 'Speech recognition unavailable — type via Command instead';
  }
  if (needsUnlock.value) {
    return 'Unlock voice first (browser requires a click), then hold Talk';
  }
  return `Hold Talk · Space hold-to-talk · or Type to ask ${OPERATOR_PERSONA_NAME}`;
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

async function unlockVoice(): Promise<void> {
  await unlockKairoAudioPlayback();
  // #region agent log
  fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Debug-Session-Id': 'fc0b35',
    },
    body: JSON.stringify({
      sessionId: 'fc0b35',
      runId: 'voice-talk',
      hypothesisId: 'H-voice-talk',
      location: 'KairoVoiceDeckPanel.vue:unlockVoice',
      message: 'voice unlock from voice card',
      data: { mediaUnlocked: kairoAudioUnlockSnapshot.value.mediaUnlocked },
      timestamp: Date.now(),
    }),
  }).catch(() => {});
  // #endregion
}

function startManualPtt(): boolean {
  if (micDisabled.value) {
    return false;
  }
  if (needsUnlock.value) {
    void unlockVoice();
  }
  shell.interruptKairoVoice();
  const started = speechCapture.startCapture('manual', { takeover: true });
  // #region agent log
  fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Debug-Session-Id': 'fc0b35',
    },
    body: JSON.stringify({
      sessionId: 'fc0b35',
      runId: 'voice-talk',
      hypothesisId: 'H-voice-talk',
      location: 'KairoVoiceDeckPanel.vue:startManualPtt',
      message: 'voice card PTT start',
      data: {
        started,
        supported: speechCapture.supported,
        privacy: shell.operatorPresenceSettings.privacy_mode,
        centerView: shell.operatorCenterView,
      },
      timestamp: Date.now(),
    }),
  }).catch(() => {});
  // #endregion
  return started;
}

function handleMicPointerDown(event: PointerEvent): void {
  if (micDisabled.value) {
    return;
  }
  const target = event.currentTarget;
  if (target instanceof HTMLElement && target.setPointerCapture) {
    target.setPointerCapture(event.pointerId);
  }
  startManualPtt();
}

function handleMicPointerUp(event: PointerEvent): void {
  const target = event.currentTarget;
  if (target instanceof HTMLElement && target.releasePointerCapture) {
    try {
      if (target.hasPointerCapture(event.pointerId)) {
        target.releasePointerCapture(event.pointerId);
      }
    } catch {
      // already released
    }
  }
  if (speechCapture.capturing.value && speechCapture.captureMode.value === 'manual') {
    speechCapture.stopCapture();
  }
}

function openTypeToAsk(): void {
  shell.setDockHeroMode('command');
  shell.focusCommandSeam();
}

function handleSpaceHotkey(event: KeyboardEvent): void {
  // Brain view already owns Space via KairoConversationBar.
  if (shell.operatorBrainGalaxyActive || shell.layoutMode !== 'operator') {
    return;
  }
  if (event.code !== 'Space' || event.repeat) {
    return;
  }
  const target = event.target;
  if (
    target instanceof HTMLElement &&
    (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)
  ) {
    return;
  }
  if (micDisabled.value) {
    return;
  }
  if (speechCapture.capturing.value && speechCapture.captureMode.value === 'manual') {
    event.preventDefault();
    return;
  }
  event.preventDefault();
  startManualPtt();
}

function handleSpaceKeyup(event: KeyboardEvent): void {
  if (shell.operatorBrainGalaxyActive || shell.layoutMode !== 'operator') {
    return;
  }
  if (event.code !== 'Space') {
    return;
  }
  if (speechCapture.capturing.value && speechCapture.captureMode.value === 'manual') {
    speechCapture.stopCapture();
  }
}

onMounted(() => {
  refreshSpeakingState();
  unsubscribeSpeaking = subscribeKairoVoiceSpeaking((active) => {
    speaking.value = active;
  });
  void refreshVoiceLog();
  window.addEventListener('keydown', handleSpaceHotkey, true);
  window.addEventListener('keyup', handleSpaceKeyup, true);
  // #region agent log
  requestAnimationFrame(() => {
    const deck = voiceDeckRef.value;
    const anchor = deck?.closest('.left-sidebar-mockup__status-anchor') as HTMLElement | null;
    const sidebar = deck?.closest('.left-sidebar-mockup') as HTMLElement | null;
    const workspacePanel = sidebar?.querySelector(
      '.left-sidebar-mockup__workspaces-panel',
    ) as HTMLElement | null;
    if (!deck || !anchor || !sidebar) return;
    const deckBox = deck.getBoundingClientRect();
    const anchorBox = anchor.getBoundingClientRect();
    const sidebarBox = sidebar.getBoundingClientRect();
    const workspaceBox = workspacePanel?.getBoundingClientRect();
    fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Debug-Session-Id': 'fc0b35',
      },
      body: JSON.stringify({
        sessionId: 'fc0b35',
        runId: 'voice-placement',
        hypothesisId: 'H-voice-anchor',
        location: 'KairoVoiceDeckPanel.vue:onMounted',
        message: 'voice deck placement inside left rail',
        data: {
          sidebarH: Math.round(sidebarBox.height),
          workspaceH: Math.round(workspaceBox?.height ?? 0),
          anchorH: Math.round(anchorBox.height),
          deckH: Math.round(deckBox.height),
          gapWorkspaceToAnchor: workspaceBox
            ? Math.round(anchorBox.top - workspaceBox.bottom)
            : null,
          gapDeckToAnchorBottom: Math.round(anchorBox.bottom - deckBox.bottom),
          gapDeckToSidebarBottom: Math.round(sidebarBox.bottom - deckBox.bottom),
          anchorDisplay: getComputedStyle(anchor).display,
          anchorFlex: getComputedStyle(anchor).flex,
          anchorMarginTop: getComputedStyle(anchor).marginTop,
          devDiagnostics: Boolean(deck.querySelector('.kairo-voice-deck__dev-diagnostics')),
        },
        timestamp: Date.now(),
      }),
    }).catch(() => {});
  });
  // #endregion
});

onBeforeUnmount(() => {
  unsubscribeSpeaking?.();
  window.removeEventListener('keydown', handleSpaceHotkey, true);
  window.removeEventListener('keyup', handleSpaceKeyup, true);
});
</script>

<template>
  <section
    ref="voiceDeckRef"
    class="kairo-voice-deck hud-panel-frame"
    :class="[
      `kairo-voice-deck--${presenceState}`,
      { 'kairo-voice-deck--speaking': speaking },
      { 'kairo-voice-deck--listening': listening },
      { 'kairo-voice-deck--galaxy-compact': shell.operatorBrainGalaxyActive },
    ]"
    aria-label="Operator voice control"
  >
    <div class="kairo-voice-deck__hud" aria-hidden="true">
      <span class="kairo-voice-deck__hud-grid" />
      <span class="kairo-voice-deck__hud-scan" />
      <span class="kairo-voice-deck__hud-glow" />
      <span class="kairo-voice-deck__hud-corner kairo-voice-deck__hud-corner--tl" />
      <span class="kairo-voice-deck__hud-corner kairo-voice-deck__hud-corner--tr" />
      <span class="kairo-voice-deck__hud-corner kairo-voice-deck__hud-corner--bl" />
      <span class="kairo-voice-deck__hud-corner kairo-voice-deck__hud-corner--br" />
    </div>

    <header class="kairo-voice-deck__persona-row">
      <p class="kairo-voice-deck__title">
        <PersonaTitle suffix="Voice" mark-size="xs" />
      </p>
      <span
        class="kairo-voice-deck__meter"
        :class="{
          'kairo-voice-deck__meter--active': listening || speaking,
        }"
        aria-hidden="true"
      >
        <i /><i /><i /><i /><i /><i />
      </span>
    </header>

    <p class="kairo-voice-deck__status-chip">
      <span class="kairo-voice-deck__live-dot" aria-hidden="true" />
      {{ listening ? 'Listening' : speaking ? 'Speaking' : presenceState }}
    </p>

    <div class="kairo-voice-deck__cinematic-body">
      <div
        v-if="!shell.operatorBrainGalaxyActive"
        class="kairo-voice-deck__orb-stage"
      >
        <HudHoloVoiceOrb
          :active="true"
          :listening="listening"
          :speaking="speaking"
        />
      </div>

      <div class="kairo-voice-deck__copy">
        <div class="kairo-voice-deck__rhythm-block">
          <p class="kairo-voice-deck__section-label">Live</p>
          <p class="kairo-voice-deck__line">{{ liveLine }}</p>
        </div>
        <template v-if="!shell.operatorBrainGalaxyActive">
          <div class="kairo-voice-deck__rhythm-block kairo-voice-deck__rhythm-block--prompt">
            <p class="kairo-voice-deck__section-label">Prompt</p>
            <p class="kairo-voice-deck__hint">{{ talkHint }}</p>
          </div>
          <p
            v-if="captureError"
            class="kairo-voice-deck__error"
            role="alert"
          >
            {{ captureError }}
          </p>
          <details v-if="showDevVoiceDiagnostics" class="kairo-voice-deck__dev-diagnostics">
            <summary>Voice diagnostics</summary>
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
          </details>
        </template>
      </div>
    </div>

    <div
      v-if="!shell.operatorBrainGalaxyActive"
      class="kairo-voice-deck__actions"
    >
      <button
        v-if="needsUnlock"
        type="button"
        class="kairo-voice-deck__action kairo-voice-deck__action--primary"
        @click="unlockVoice"
      >
        Unlock voice
      </button>
      <button
        type="button"
        class="kairo-voice-deck__action kairo-voice-deck__action--talk"
        :class="{ 'kairo-voice-deck__action--talking': listening }"
        :disabled="micDisabled"
        :title="micDisabled ? talkHint : 'Hold to talk to VAXON'"
        @pointerdown.prevent="handleMicPointerDown"
        @pointerup.prevent="handleMicPointerUp"
        @pointercancel.prevent="handleMicPointerUp"
        @lostpointercapture="handleMicPointerUp"
      >
        {{ listening ? 'Listening…' : 'Hold to talk' }}
      </button>
      <button
        type="button"
        class="kairo-voice-deck__action"
        @click="openTypeToAsk"
      >
        Type to ask
      </button>
    </div>
  </section>
</template>
