import { onBeforeUnmount } from 'vue';

import { useShellStore } from '../../stores/shell';
import { registerKairoConversationSubmit } from './kairo-conversation-bus';
import { kairoConversationPhase } from './kairo-conversation-state';
import { useKairoHandsFreeLoop } from './use-kairo-hands-free-loop';
import { useKairoConversation } from './use-kairo-conversation';
import { setKairoSpeechPrivacyBlocked } from './kairo-shared-speech-capture';
import { useKairoVoiceInterrupt } from './use-kairo-voice-interrupt';
import { setKairoSpeechTuningProvider } from '../../lib/kairo-voice-playback';

/**
 * App-scoped voice loop: hands-free listening stays active across Mission Control
 * views and IDE mode whenever the operator enables it in settings.
 */
export function useKairoAppVoice(): void {
  const shell = useShellStore();
  // App voice and typed surfaces use the same awaited turn-submission function.
  const { submitTurn } = useKairoConversation();

  setKairoSpeechPrivacyBlocked(() => shell.operatorPresenceSettings.privacy_mode);
  setKairoSpeechTuningProvider(() => ({
    rate: shell.operatorPresenceSettings.speech_rate ?? 1.0,
    pitch: shell.operatorPresenceSettings.speech_pitch ?? 1.04,
    voice: shell.operatorPresenceSettings.azure_voice_id ?? 'en-GB-RyanNeural',
  }));
  useKairoVoiceInterrupt();

  useKairoHandsFreeLoop({
    enabled: () => shell.operatorPresenceSettings.hands_free_enabled === true,
    privacyBlocked: () => shell.operatorPresenceSettings.privacy_mode,
    kairoSpeaking: () => shell.kairoSpeechActive,
    conversationPending: () =>
      kairoConversationPhase.value === 'thinking' || kairoConversationPhase.value === 'speaking',
  });

  const unregisterSubmit = registerKairoConversationSubmit(submitTurn);

  onBeforeUnmount(() => {
    unregisterSubmit();
  });
}
