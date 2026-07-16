import { computed, onBeforeUnmount, ref } from 'vue';

import { postKairoConverse } from '../../lib/kairo-converse-client';
import { parseChatUiAction } from '../../lib/chat-ui-action';
import { normalizeKairoCopy, normalizeVoiceTranscript, canonicalWorkspaceLabel } from '../../lib/kairo-entity-labels';
import { recordOperatorArtifacts } from '../../lib/operator-artifact-view';
import {
  formatConversationDisplayReply,
  sanitizeSpokenReply,
} from '../../lib/sanitize-spoken-reply';
import { clearKairoVoiceFollowupWindow } from '../../lib/kairo-voice-followup-window';
import type { KairoVoiceCaptureMode } from '../../lib/kairo-voice-gate';
import { useShellStore } from '../../stores/shell';
import { resolveConversationNavigationIntent, workspaceGalaxyNodeId } from './conversation-intents';
import { dispatchKairoConverseOutcome } from './kairo-conversation-dispatch';
import {
  clearBriefingSurfaceOffer,
  mentionsBriefingSurfaceOffer,
  scheduleBriefingSurfaceOffer,
} from './conversation-briefing-surface';
import {
  kairoConversationError,
  kairoConversationPhase,
  kairoConversationReply,
  setKairoConversationPhase,
} from './kairo-conversation-state';
import { brainGalaxyConversationFocus, setBrainGalaxyConversationFocus } from '../brain-galaxy/brain-galaxy-focus';
import { useKairoSpeechCapture } from './use-kairo-speech-capture';
import {
  CONTINUE_VOICE_RE,
  createKairoConversationTurnHandlers,
  HANDOFF_CLIENT_RE,
} from './kairo-conversation-turn-handlers';
import {
  createKairoRuntimeAssistantCue,
  createKairoVoiceDelivery,
} from './kairo-conversation-voice-runtime';

export function useKairoConversation() {
  const shell = useShellStore();
  const draft = ref('');
  const pending = ref(false);
  const thinkingLine = ref('');
  let lastOperatorPrompt = '';

  const canSubmit = computed(
    () =>
      draft.value.trim().length > 0 &&
      !pending.value &&
      kairoConversationPhase.value !== 'thinking',
  );
  const workspaceId = computed(() => shell.currentWorkspace?.workspace_id ?? '');

  const speechCapture = useKairoSpeechCapture({
    privacyBlocked: () => shell.operatorPresenceSettings.privacy_mode,
    sttMode: () => shell.operatorPresenceSettings.stt_mode, captureMode: 'manual',
    stopOnUnmount: 'manual_only',
  });

  function kairoSpeechSessionId(): string {
    return shell.kairoSpeechSessionId();
  }

  function speakReply(line: string, operatorPrompt?: string): Promise<void> {
    return shell.speakKairoConversationLine(line, {
      operatorPrompt: operatorPrompt ?? lastOperatorPrompt,
      skipSpeakApi: true,
    });
  }

  const {
    clearRuntimeAssistantCue,
    scheduleRuntimeAssistantCue,
    determineAnswerTier,
    thinkingStatusLine,
  } = createKairoRuntimeAssistantCue({ shell, pending });

  const { deliverVoiceReply } = createKairoVoiceDelivery({ shell, speakReply });

  const {
    executeConverseAction,
    tryBriefingSurfaceFollowup,
    tryClientHandoff,
    tryResumeCurrentRun,
  } = createKairoConversationTurnHandlers({
    shell,
    draft,
    pending,
    thinkingLine,
    deliverVoiceReply,
    speakReply,
  });

  async function speakReplyFromExternal(
    reply: string,
    voiceCaptureMode?: KairoVoiceCaptureMode,
    operatorPrompt?: string,
  ): Promise<void> {
    if (operatorPrompt?.trim()) {
      lastOperatorPrompt = operatorPrompt.trim();
    }
    await deliverVoiceReply(reply, voiceCaptureMode);
  }

  async function submitTurn(
    rawContent?: string,
    options?: { voiceCaptureMode?: KairoVoiceCaptureMode },
  ): Promise<void> {
    const content = normalizeVoiceTranscript((rawContent ?? draft.value).trim());
    if (!content || pending.value) {
      return;
    }
    lastOperatorPrompt = content;
    const answerTier = determineAnswerTier(content);

    pending.value = true;
    kairoConversationError.value = null;
    thinkingLine.value = thinkingStatusLine(content, answerTier);
    clearKairoVoiceFollowupWindow();
    setKairoConversationPhase('thinking');
    if (answerTier === 'deep') {
      scheduleRuntimeAssistantCue(content);
    }

    const navIntent = resolveConversationNavigationIntent(
      content,
      shell.workspaces.map((workspace) => ({
        workspace_id: workspace.workspace_id,
        display_name: canonicalWorkspaceLabel(
          workspace.workspace_id,
          workspace.display_name ?? workspace.workspace_id,
        ),
      })),
    );

    if (navIntent) {
      clearRuntimeAssistantCue();
      if (navIntent.kind === 'focus_attention') {
        shell.focusAttentionSidebar();
      } else if (navIntent.kind === 'focus_briefing') {
        clearBriefingSurfaceOffer();
        shell.focusKairoBriefing();
      } else if (navIntent.kind === 'focus_workspace' && navIntent.workspaceId) {
        shell.setOperatorCenterView('graph');
        shell.setCurrentWorkspace(navIntent.workspaceId);
        const label = canonicalWorkspaceLabel(
          navIntent.workspaceId,
          shell.workspaces.find((workspace) => workspace.workspace_id === navIntent.workspaceId)
            ?.display_name ?? navIntent.workspaceId,
        );
        setBrainGalaxyConversationFocus({
          nodeId: workspaceGalaxyNodeId(navIntent.workspaceId),
          workspaceId: navIntent.workspaceId,
          signalId: null,
          label,
        });
      } else if (navIntent.kind === 'switch_center_view' && navIntent.centerView) {
        shell.setOperatorCenterView(navIntent.centerView);
      }
      draft.value = '';
      pending.value = false;
      thinkingLine.value = '';
      await deliverVoiceReply(navIntent.reply, options?.voiceCaptureMode);
      return;
    }

    if (await tryBriefingSurfaceFollowup(content, options)) {
      clearRuntimeAssistantCue();
      return;
    }

    if (await tryResumeCurrentRun(content, options)) {
      clearRuntimeAssistantCue();
      draft.value = '';
      pending.value = false;
      thinkingLine.value = '';
      return;
    }

    try {
      const response = await postKairoConverse({
        content,
        session_id: kairoSpeechSessionId(),
        workspace_id: workspaceId.value,
        use_runtime: answerTier === 'deep',
        answer_tier: answerTier,
        context_workspace_id: brainGalaxyConversationFocus.value?.workspaceId ?? workspaceId.value,
        context_signal_id: brainGalaxyConversationFocus.value?.signalId ?? '',
        context_node_id: brainGalaxyConversationFocus.value?.nodeId ?? '',
      });
      clearRuntimeAssistantCue();
      if (response.artifacts.length) {
        recordOperatorArtifacts(response.artifacts, parseChatUiAction);
      }
      if (!response.action && HANDOFF_CLIENT_RE.test(content)) {
        if (await tryClientHandoff(content)) {
          draft.value = '';
          pending.value = false;
          thinkingLine.value = '';
          return;
        }
      }
      kairoConversationReply.value = normalizeKairoCopy(
        formatConversationDisplayReply(response.reply) || sanitizeSpokenReply(response.reply),
      );
      draft.value = '';
      pending.value = false;
      thinkingLine.value = '';
      await dispatchKairoConverseOutcome(shell, response, executeConverseAction);
      if (mentionsBriefingSurfaceOffer(response.reply)) {
        scheduleBriefingSurfaceOffer();
      }
      await deliverVoiceReply(response.reply, options?.voiceCaptureMode);
    } catch (error) {
      clearRuntimeAssistantCue();
      kairoConversationError.value =
        error instanceof Error ? error.message : 'KAIRO conversation failed';
      setKairoConversationPhase('idle');
      pending.value = false;
      thinkingLine.value = '';
    } finally {
      clearRuntimeAssistantCue();
      if (pending.value) {
        pending.value = false;
      }
    }
  }

  function handleFocus(): void {
    if (kairoConversationPhase.value === 'thinking' || pending.value) {
      return;
    }
  }

  function handleBlur(): void {
    if (kairoConversationPhase.value === 'listening' && !speechCapture.capturing.value) {
      setKairoConversationPhase('idle');
    }
  }

  function startVoiceCapture(): boolean {
    shell.interruptKairoVoice();
    return speechCapture.startCapture();
  }

  function stopVoiceCapture(): void {
    speechCapture.stopCapture();
  }

  onBeforeUnmount(() => {
    clearRuntimeAssistantCue();
  });

  return {
    draft,
    pending,
    thinkingLine,
    canSubmit,
    speakReplyFromExternal,
    executeConverseAction,
    submitTurn,
    handleFocus,
    handleBlur,
    speechCapture,
    startVoiceCapture,
    stopVoiceCapture,
  };
}
