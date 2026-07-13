import { onBeforeUnmount } from 'vue';

import { postKairoConverse } from '../../lib/kairo-converse-client';
import { parseChatUiAction } from '../../lib/chat-ui-action';
import { normalizeKairoCopy } from '../../lib/kairo-entity-labels';
import { formatConversationDisplayReply, sanitizeSpokenReply } from '../../lib/sanitize-spoken-reply';
import { recordOperatorArtifacts } from '../../lib/operator-artifact-view';
import { useShellStore } from '../../stores/shell';
import { registerKairoConversationSubmit, type KairoConversationSubmitOptions } from './kairo-conversation-bus';
import { kairoConversationError, kairoConversationReply, kairoConversationPhase, setKairoConversationPhase } from './kairo-conversation-state';
import { mentionsBriefingSurfaceOffer, scheduleBriefingSurfaceOffer } from './conversation-briefing-surface';
import { shouldAutoDispatchConverseCommand } from './conversation-command-policy';
import { useKairoHandsFreeLoop } from './use-kairo-hands-free-loop';
import { useKairoConversation } from './use-kairo-conversation';
import { setKairoSpeechPrivacyBlocked } from './kairo-shared-speech-capture';
import { useKairoVoiceInterrupt } from './use-kairo-voice-interrupt';

/**
 * App-scoped voice loop: hands-free listening stays active across Mission Control
 * views and IDE mode whenever the operator enables it in settings.
 */
export function useKairoAppVoice(): void {
  const shell = useShellStore();
  const { speakReplyFromExternal } = useKairoConversation();
  let lastOperatorPrompt = '';

  setKairoSpeechPrivacyBlocked(() => shell.operatorPresenceSettings.privacy_mode);
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
          use_runtime: false,
          answer_tier: 'fast',
          context_workspace_id: shell.currentWorkspace?.workspace_id ?? '',
        });
        if (response.artifacts.length) {
          recordOperatorArtifacts(response.artifacts, parseChatUiAction);
        }
        kairoConversationReply.value = normalizeKairoCopy(
          formatConversationDisplayReply(response.reply) || sanitizeSpokenReply(response.reply),
        );
        if (response.action) {
          if (response.action.type === 'focus_briefing') {
            shell.focusKairoBriefing();
          } else if (response.action.type === 'dispatch_command') {
            await shell.submitOperatorCommandContent(response.action.content);
          } else if (response.action.type === 'handoff_signal') {
            await shell.handoffSignalToIde({
              signal_id: response.action.signal_id,
              workspace_id: response.action.target_workspace_id,
              title: response.action.task.replace(/^Investigate signal "/, '').split('"')[0] ?? response.action.task,
              summary: response.action.task,
            });
          }
        } else if (shouldAutoDispatchConverseCommand(response)) {
          await shell.submitOperatorCommandContent(response.command_content!);
        }
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
