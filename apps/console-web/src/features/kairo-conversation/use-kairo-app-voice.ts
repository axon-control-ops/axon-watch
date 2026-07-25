import { onBeforeUnmount, watch } from 'vue';

import { kairoAudioUnlockSnapshot, onKairoAudioUnlocked } from '../../lib/kairo-audio-unlock';
import { scheduleKairoVoiceFollowupWindowAfterSpeech } from '../../lib/kairo-voice-followup-window';
import { speakKairoLine } from '../../lib/kairo-voice-playback';
import { shouldEnableKairoHandsFreeLoop } from '../../lib/kairo-hands-free-armed';
import { useShellStore } from '../../stores/shell';
import { registerKairoConversationSubmit } from './kairo-conversation-bus';
import { kairoConversationPhase } from './kairo-conversation-state';
import { useKairoHandsFreeLoop } from './use-kairo-hands-free-loop';
import { useKairoConversation } from './use-kairo-conversation';
import { setKairoSpeechPrivacyBlocked, setKairoSpeechSttMode } from './kairo-shared-speech-capture';
import { useKairoVoiceInterrupt } from './use-kairo-voice-interrupt';
import { setKairoSpeechTuningProvider } from '../../lib/kairo-voice-playback';

const SESSION_READY_KEY = 'axon-x-duplex-session-ready';

/**
 * App-scoped voice loop: hands-free listening stays active across Mission Control
 * views and IDE mode whenever the operator enables it in settings.
 */
export function useKairoAppVoice(): void {
  const shell = useShellStore();
  // App voice and typed surfaces use the same awaited turn-submission function.
  const { submitTurn } = useKairoConversation();

  setKairoSpeechPrivacyBlocked(() => shell.operatorPresenceSettings.privacy_mode);
  setKairoSpeechSttMode(() => shell.operatorPresenceSettings.stt_mode);
  setKairoSpeechTuningProvider(() => ({
    rate: shell.operatorPresenceSettings.speech_rate ?? 1.0,
    pitch: shell.operatorPresenceSettings.speech_pitch ?? 1.04,
    voice: shell.operatorPresenceSettings.azure_voice_id ?? 'en-GB-RyanNeural',
  }));
  useKairoVoiceInterrupt();

  useKairoHandsFreeLoop({
    enabled: () =>
      shouldEnableKairoHandsFreeLoop(
        shell.operatorPresenceSettings,
        kairoAudioUnlockSnapshot.value.mediaUnlocked,
      ),
    privacyBlocked: () => shell.operatorPresenceSettings.privacy_mode,
    kairoSpeaking: () => shell.kairoSpeechActive,
    conversationPending: () =>
      kairoConversationPhase.value === 'thinking' || kairoConversationPhase.value === 'speaking',
  });

  async function maybeSpeakDuplexSessionReady(): Promise<void> {
    const settings = shell.operatorPresenceSettings;
    if (!settings.proactive_duplex_enabled || settings.privacy_mode) {
      return;
    }
    if (settings.kairo_narration === 'off') {
      return;
    }
    if (!kairoAudioUnlockSnapshot.value.mediaUnlocked) {
      return;
    }
    if (typeof sessionStorage !== 'undefined' && sessionStorage.getItem(SESSION_READY_KEY) === '1') {
      return;
    }
    try {
      sessionStorage.setItem(SESSION_READY_KEY, '1');
    } catch {
      // ignore
    }
    scheduleKairoVoiceFollowupWindowAfterSpeech();
    await speakKairoLine(
      'VAXON online. I am listening. After I speak, answer naturally — or say VAXON anytime.',
      { priority: 'conversation' },
    );
  }

  const stopUnlockWatch = watch(
    () =>
      [
        kairoAudioUnlockSnapshot.value.mediaUnlocked,
        shell.operatorPresenceSettings.proactive_duplex_enabled,
      ] as const,
    ([mediaUnlocked, duplex]) => {
      if (mediaUnlocked && duplex) {
        void maybeSpeakDuplexSessionReady();
      }
    },
    { immediate: true },
  );

  const unregisterUnlock = onKairoAudioUnlocked(() => {
    void maybeSpeakDuplexSessionReady();
  });

  const unregisterSubmit = registerKairoConversationSubmit(submitTurn);

  onBeforeUnmount(() => {
    unregisterSubmit();
    unregisterUnlock();
    stopUnlockWatch();
  });
}
