import { onBeforeUnmount } from 'vue';

import { postKairoConverse } from '../../lib/kairo-converse-client';
import { parseChatUiAction } from '../../lib/chat-ui-action';
import { normalizeKairoCopy } from '../../lib/kairo-entity-labels';
import { formatConversationDisplayReply, sanitizeSpokenReply } from '../../lib/sanitize-spoken-reply';
import { recordOperatorArtifacts } from '../../lib/operator-artifact-view';
import { useShellStore } from '../../stores/shell';
import { registerKairoConversationSubmit, type KairoConversationSubmitOptions } from './kairo-conversation-bus';
import {
  kairoConversationError,
  kairoConversationReply,
  kairoConversationPhase,
  setKairoConversationPhase,
} from './kairo-conversation-state';
import { mentionsBriefingSurfaceOffer, scheduleBriefingSurfaceOffer } from './conversation-briefing-surface';
import { dispatchKairoConverseOutcome } from './kairo-conversation-dispatch';
import { executeKairoConverseAction } from './execute-kairo-converse-action';
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
  // Speech/TTS helpers only — do not create a second draft/input conversation instance.
  const { speakReplyFromExternal } = useKairoConversation();
  let lastOperatorPrompt = '';

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

  const unregisterSubmit = registerKairoConversationSubmit(
    async (content: string, options?: KairoConversationSubmitOptions) => {
      const trimmed = content.trim();
      if (!trimmed) {
        return;
      }
      lastOperatorPrompt = trimmed;
      kairoConversationError.value = null;
      setKairoConversationPhase('thinking');
      try {
        const response = await postKairoConverse({
          content: trimmed,
          session_id: shell.kairoSpeechSessionId(),
          workspace_id: shell.currentWorkspace?.workspace_id ?? '',
          use_runtime:
            shell.operatorPresenceSettings.voice_routing_mode === 'runtime_aggressive',
          answer_tier: 'fast',
          context_workspace_id: shell.currentWorkspace?.workspace_id ?? '',
        });
        if (response.artifacts.length) {
          recordOperatorArtifacts(response.artifacts, parseChatUiAction);
        }
        kairoConversationReply.value = normalizeKairoCopy(
          formatConversationDisplayReply(response.reply) || sanitizeSpokenReply(response.reply),
        );
        await dispatchKairoConverseOutcome(
          shell,
          response,
          (action) => executeKairoConverseAction(shell, action),
          'voice',
        );
        if (mentionsBriefingSurfaceOffer(response.reply)) {
          scheduleBriefingSurfaceOffer();
        }
        await speakReplyFromExternal(
          sanitizeSpokenReply(response.reply) || kairoConversationReply.value,
          options?.voiceCaptureMode,
          lastOperatorPrompt,
        );
      } catch (error) {
        kairoConversationError.value =
          error instanceof Error ? error.message : 'KAIRO conversation failed';
        setKairoConversationPhase('idle');
      }
    },
  );

  onBeforeUnmount(() => {
    unregisterSubmit();
  });
}
