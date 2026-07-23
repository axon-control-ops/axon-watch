import { computed, onBeforeUnmount, ref } from 'vue';

import { normalizeVoiceTranscript } from '../../lib/kairo-entity-labels';
import { clearKairoVoiceFollowupWindow } from '../../lib/kairo-voice-followup-window';
import { recordVoiceLoopDiagnostic } from '../../lib/kairo-voice-loop-diagnostics';
import type { KairoVoiceCaptureMode } from '../../lib/kairo-voice-gate';
import { useShellStore } from '../../stores/shell';
import { handleConversationModelSwitchIntent } from './conversation-model-switch-handler';
import {
  applyKairoConversationNavigationIntent,
  resolveKairoConversationNavigationIntent,
} from './conversation-navigation-handler';
import {
  kairoConversationError,
  kairoConversationPhase,
  setKairoConversationPhase,
} from './kairo-conversation-state';
import { brainGalaxyConversationFocus } from '../brain-galaxy/brain-galaxy-focus';
import { useKairoSpeechCapture } from './use-kairo-speech-capture';
import { createKairoConversationTurnHandlers } from './kairo-conversation-turn-handlers';
import {
  createKairoRuntimeAssistantCue,
  createKairoVoiceDelivery,
} from './kairo-conversation-voice-runtime';
import { runKairoConverseSubmit } from './run-kairo-converse-submit';

export function useKairoConversation() {
  const shell = useShellStore();
  const draft = ref('');
  const pending = ref(false);
  const thinkingLine = ref('');
  let lastOperatorPrompt = '';
  let activeConverseAbort: AbortController | null = null;

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

  function closeTurnSurface(options?: { keepPhase?: boolean }): void {
    draft.value = '';
    pending.value = false;
    thinkingLine.value = '';
    if (!options?.keepPhase && kairoConversationPhase.value === 'thinking') {
      setKairoConversationPhase('idle');
    }
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
    const converseStartedAt = Date.now();

    activeConverseAbort?.abort();
    activeConverseAbort = new AbortController();
    const abortSignal = activeConverseAbort.signal;

    pending.value = true;
    kairoConversationError.value = null;
    thinkingLine.value = thinkingStatusLine(content, answerTier);
    clearKairoVoiceFollowupWindow();
    setKairoConversationPhase('thinking');
    recordVoiceLoopDiagnostic({
      kind: 'converse_start',
      phase: 'thinking',
      reason: answerTier,
    });
    if (answerTier === 'deep') {
      scheduleRuntimeAssistantCue(content);
      window.setTimeout(() => {
        if (!pending.value || kairoConversationPhase.value !== 'thinking') {
          return;
        }
        thinkingLine.value = 'Still working — I will answer or time out shortly…';
        recordVoiceLoopDiagnostic({
          kind: 'converse_progress',
          phase: 'thinking',
          latencyMs: Date.now() - converseStartedAt,
        });
      }, 4_000);
    }

    const modelHandled = await handleConversationModelSwitchIntent({
      shell,
      content,
      voiceCaptureMode: options?.voiceCaptureMode,
      clearRuntimeAssistantCue,
      deliverVoiceReply,
      resetDraftState: () => closeTurnSurface(),
    });
    if (modelHandled) {
      clearRuntimeAssistantCue();
      closeTurnSurface();
      return;
    }

    const navIntent = resolveKairoConversationNavigationIntent(content, shell);

    if (navIntent) {
      clearRuntimeAssistantCue();
      await applyKairoConversationNavigationIntent({
        shell,
        navIntent,
        deliverVoiceReply,
        voiceCaptureMode: options?.voiceCaptureMode,
        resetDraftState: () => closeTurnSurface(),
      });
      clearRuntimeAssistantCue();
      closeTurnSurface();
      return;
    }

    if (await tryBriefingSurfaceFollowup(content, options)) {
      clearRuntimeAssistantCue();
      closeTurnSurface();
      return;
    }

    if (await tryResumeCurrentRun(content, options)) {
      clearRuntimeAssistantCue();
      closeTurnSurface();
      return;
    }

    await runKairoConverseSubmit({
      shell,
      content,
      answerTier,
      converseStartedAt,
      abortSignal,
      sessionId: kairoSpeechSessionId(),
      workspaceId: workspaceId.value,
      contextWorkspaceId: brainGalaxyConversationFocus.value?.workspaceId ?? workspaceId.value,
      contextSignalId: brainGalaxyConversationFocus.value?.signalId ?? '',
      contextNodeId: brainGalaxyConversationFocus.value?.nodeId ?? '',
      voiceCaptureMode: options?.voiceCaptureMode,
      deliverVoiceReply,
      executeConverseAction,
      tryClientHandoff,
      closeTurnSurface,
      clearRuntimeAssistantCue,
      pending,
    });

    if (activeConverseAbort?.signal === abortSignal) {
      activeConverseAbort = null;
    }
    thinkingLine.value = '';
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
    activeConverseAbort?.abort();
    activeConverseAbort = null;
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
