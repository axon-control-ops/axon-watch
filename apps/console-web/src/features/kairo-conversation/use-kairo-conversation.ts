import { computed, onBeforeUnmount, ref } from 'vue';

import {
  postKairoConverse,
  type KairoConverseAnswerTier,
} from '../../lib/kairo-converse-client';
import { parseChatUiAction } from '../../lib/chat-ui-action';
import { normalizeKairoCopy, normalizeVoiceTranscript, canonicalWorkspaceLabel } from '../../lib/kairo-entity-labels';
import { recordOperatorArtifacts } from '../../lib/operator-artifact-view';
import {
  formatConversationDisplayReply,
  sanitizeSpokenReply,
} from '../../lib/sanitize-spoken-reply';
import {
  clearKairoVoiceFollowupWindow,
  finalizeKairoVoiceFollowupWindow,
  scheduleKairoVoiceFollowupWindowAfterSpeech,
} from '../../lib/kairo-voice-followup-window';
import type { KairoVoiceCaptureMode } from '../../lib/kairo-voice-gate';
import { useShellStore } from '../../stores/shell';
import { resolveConversationNavigationIntent } from './conversation-intents';
import {
  kairoConversationError,
  kairoConversationPhase,
  kairoConversationReply,
  setKairoConversationPhase,
} from './kairo-conversation-state';
import {
  RUNTIME_ASSISTANT_CUE_COPY,
  RUNTIME_ASSISTANT_CUE_LINE,
  shouldPrimeRuntimeAssistantCue,
} from './runtime-assistant-heuristics';
import { brainGalaxyConversationFocus } from '../brain-galaxy/brain-galaxy-focus';
import { useKairoSpeechCapture } from './use-kairo-speech-capture';
import { useKairoVoiceInterrupt } from './use-kairo-voice-interrupt';

const HANDOFF_CLIENT_RE = /\b(hand\s*off|handoff|continue in ide|investigate in ide)\b/i;
const RUNTIME_ASSISTANT_CUE_DELAY_MS = 1200;

export function useKairoConversation() {
  const shell = useShellStore();
  const draft = ref('');
  const pending = ref(false);
  const thinkingLine = ref('');
  let runtimeCueTimer: ReturnType<typeof globalThis.setTimeout> | null = null;

  const canSubmit = computed(
    () =>
      draft.value.trim().length > 0 &&
      !pending.value &&
      kairoConversationPhase.value !== 'thinking',
  );
  const workspaceId = computed(() => shell.currentWorkspace?.workspace_id ?? '');

  const speechCapture = useKairoSpeechCapture({
    privacyBlocked: () => shell.operatorPresenceSettings.privacy_mode,
    captureMode: 'manual',
  });

  useKairoVoiceInterrupt();

  function kairoSpeechSessionId(): string {
    const key = 'axon-x:kairo-speech-session';
    if (typeof sessionStorage === 'undefined') {
      return 'default';
    }
    let id = sessionStorage.getItem(key);
    if (!id) {
      id = `kairo-${Date.now()}`;
      sessionStorage.setItem(key, id);
    }
    return id;
  }

  function speakReply(line: string): Promise<void> {
    return shell.speakKairoConversationLine(line, { skipSpeakApi: true });
  }

  function clearRuntimeAssistantCue(): void {
    if (runtimeCueTimer !== null) {
      globalThis.clearTimeout(runtimeCueTimer);
      runtimeCueTimer = null;
    }
  }

  function scheduleRuntimeAssistantCue(content: string): void {
    clearRuntimeAssistantCue();
    if (!shouldPrimeRuntimeAssistantCue(content)) {
      return;
    }
    kairoConversationReply.value = RUNTIME_ASSISTANT_CUE_COPY;
    runtimeCueTimer = globalThis.setTimeout(() => {
      runtimeCueTimer = null;
      if (!pending.value) {
        return;
      }
      kairoConversationReply.value = RUNTIME_ASSISTANT_CUE_COPY;
      void shell.speakKairoConversationLine(RUNTIME_ASSISTANT_CUE_LINE, { skipSpeakApi: true });
    }, RUNTIME_ASSISTANT_CUE_DELAY_MS);
  }

  function determineAnswerTier(content: string): KairoConverseAnswerTier {
    return shouldPrimeRuntimeAssistantCue(content) ? 'deep' : 'fast';
  }

  function thinkingStatusLine(
    content: string,
    answerTier: KairoConverseAnswerTier,
  ): string {
    if (answerTier === 'deep') {
      return 'Consulting runtime context and shaping a short spoken answer…';
    }
    if (brainGalaxyConversationFocus.value?.signalId) {
      return 'Checking the selected signal against the current fleet state…';
    }
    if (/\b(approval|attention|signal|status|briefing|health)\b/i.test(content)) {
      return 'Scanning live operator state and briefing signals…';
    }
    return 'Checking the current operator state…';
  }

  function shouldScheduleHandsFreeFollowup(voiceCaptureMode?: KairoVoiceCaptureMode): boolean {
    return (
      shell.operatorPresenceSettings.hands_free_enabled === true &&
      voiceCaptureMode === 'hands_free'
    );
  }

  async function deliverVoiceReply(
    reply: string,
    voiceCaptureMode?: KairoVoiceCaptureMode,
  ): Promise<void> {
    const displayReply = formatConversationDisplayReply(reply);
    const spokenReply = sanitizeSpokenReply(reply);
    kairoConversationReply.value = normalizeKairoCopy(displayReply || spokenReply);
    if (shouldScheduleHandsFreeFollowup(voiceCaptureMode)) {
      scheduleKairoVoiceFollowupWindowAfterSpeech();
    }
    await speakReply(spokenReply || kairoConversationReply.value);
    finalizeKairoVoiceFollowupWindow();
  }

  async function executeConverseAction(
    action: NonNullable<Awaited<ReturnType<typeof postKairoConverse>>['action']>,
  ): Promise<void> {
    if (action.type === 'handoff_signal') {
      await shell.handoffSignalToIde({
        signal_id: action.signal_id,
        workspace_id: action.target_workspace_id,
        title: action.task.replace(/^Investigate signal "/, '').split('"')[0] ?? action.task,
        summary: action.task,
      });
      return;
    }
    if (action.type === 'dispatch_command') {
      await shell.submitOperatorCommandContent(action.content);
    }
  }

  async function tryClientHandoff(content: string): Promise<boolean> {
    if (!HANDOFF_CLIENT_RE.test(content)) {
      return false;
    }
    const topSignal = shell.operatorBriefing?.top_signals[0];
    if (!topSignal) {
      kairoConversationReply.value = 'No signal in context to hand off yet.';
      speakReply(kairoConversationReply.value);
      return true;
    }
    await shell.handoffSignalToIde({
      signal_id: topSignal.signal_id,
      workspace_id: topSignal.workspace_id,
      title: topSignal.title,
      summary: topSignal.summary,
    });
    kairoConversationReply.value = 'Handing the top signal off to the IDE.';
    speakReply(kairoConversationReply.value);
    return true;
  }

  async function submitTurn(
    rawContent?: string,
    options?: { voiceCaptureMode?: KairoVoiceCaptureMode },
  ): Promise<void> {
    const content = normalizeVoiceTranscript((rawContent ?? draft.value).trim());
    if (!content || pending.value) {
      return;
    }
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
      } else if (navIntent.kind === 'focus_workspace' && navIntent.workspaceId) {
        shell.setCurrentWorkspace(navIntent.workspaceId);
      } else if (navIntent.kind === 'switch_center_view' && navIntent.centerView) {
        shell.setOperatorCenterView(navIntent.centerView);
      }
      draft.value = '';
      pending.value = false;
      thinkingLine.value = '';
      await deliverVoiceReply(navIntent.reply, options?.voiceCaptureMode);
      return;
    }

    if (await tryClientHandoff(content)) {
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
      kairoConversationReply.value = normalizeKairoCopy(
        formatConversationDisplayReply(response.reply) || sanitizeSpokenReply(response.reply),
      );
      draft.value = '';
      pending.value = false;
      thinkingLine.value = '';
      if (response.action) {
        void executeConverseAction(response.action);
      } else if (response.turn_kind === 'command' && response.command_content) {
        void shell.submitOperatorCommandContent(response.command_content);
      } else if (response.turn_kind === 'action' && response.command_content) {
        void shell.submitOperatorCommandContent(response.command_content);
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
    if (!speechCapture.capturing.value) {
      setKairoConversationPhase('listening');
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
    submitTurn,
    handleFocus,
    handleBlur,
    speechCapture,
    startVoiceCapture,
    stopVoiceCapture,
  };
}
