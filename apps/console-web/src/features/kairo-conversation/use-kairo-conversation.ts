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
import { filterActionableOpenSignals } from '../../lib/operator-signal-count';
import { useShellStore } from '../../stores/shell';
import { resolveConversationNavigationIntent, workspaceGalaxyNodeId } from './conversation-intents';
import { shouldAutoDispatchConverseCommand } from './conversation-command-policy';
import {
  clearBriefingSurfaceOffer,
  mentionsBriefingSurfaceOffer,
  scheduleBriefingSurfaceOffer,
  shouldOpenBriefingFromFollowup,
} from './conversation-briefing-surface';
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
import { brainGalaxyConversationFocus, setBrainGalaxyConversationFocus } from '../brain-galaxy/brain-galaxy-focus';
import { useKairoSpeechCapture } from './use-kairo-speech-capture';

const HANDOFF_CLIENT_RE =
  /\b(hand\s*it\s*off|hand\s*off|handoff|continue in ide|investigate in ide|open in ide)\b/i;
const CONTINUE_VOICE_RE = /\b(continue|pick up|resume|carry on)\b/i;
const DIRECT_CONTINUE_RE =
  /^(?:a\s+)?(?:yes\s+)?(?:please\s+)?(?:continue|pick\s+up|resume|carry\s+on)\b/i;
const RUNTIME_ASSISTANT_CUE_DELAY_MS = 1200;

export function useKairoConversation() {
  const shell = useShellStore();
  const draft = ref('');
  const pending = ref(false);
  const thinkingLine = ref('');
  let runtimeCueTimer: ReturnType<typeof globalThis.setTimeout> | null = null;
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
    captureMode: 'manual',
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
      void shell.speakKairoConversationLine(RUNTIME_ASSISTANT_CUE_LINE, { operatorPrompt: content });
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
      return 'Scanning live system state and briefing signals…';
    }
    return 'Checking the current system state…';
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
    if (mentionsBriefingSurfaceOffer(displayReply || spokenReply || reply)) {
      scheduleBriefingSurfaceOffer();
    }
    if (shouldScheduleHandsFreeFollowup(voiceCaptureMode)) {
      scheduleKairoVoiceFollowupWindowAfterSpeech();
    }
    await speakReply(spokenReply || kairoConversationReply.value);
    finalizeKairoVoiceFollowupWindow();
  }

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

  async function executeConverseAction(
    action: NonNullable<Awaited<ReturnType<typeof postKairoConverse>>['action']>,
  ): Promise<void> {
    if (action.type === 'handoff_signal') {
      await shell.handoffSignalToIde(
        {
          signal_id: action.signal_id,
          workspace_id: action.target_workspace_id,
          title: action.task.replace(/^Investigate signal "/, '').split('"')[0] ?? action.task,
          summary: action.task,
          task: action.task,
        },
        { autoSubmit: true },
      );
      return;
    }
    if (action.type === 'focus_briefing') {
      clearBriefingSurfaceOffer();
      shell.focusKairoBriefing();
      return;
    }
    if (action.type === 'dispatch_command') {
      await shell.submitOperatorCommandContent(action.content);
    }
  }

  async function tryBriefingSurfaceFollowup(
    content: string,
    options?: { voiceCaptureMode?: KairoVoiceCaptureMode },
  ): Promise<boolean> {
    if (!shouldOpenBriefingFromFollowup(content)) {
      return false;
    }
    clearBriefingSurfaceOffer();
    shell.focusKairoBriefing();
    draft.value = '';
    pending.value = false;
    thinkingLine.value = '';
    await deliverVoiceReply('Opening the briefing for you.', options?.voiceCaptureMode);
    return true;
  }

  function resolveHandoffSignal() {
    const actionableInboxSignal = filterActionableOpenSignals(shell.inboxItems)[0];
    if (actionableInboxSignal) {
      return (
        shell.inboxItems.find((item) => item.signal_id === actionableInboxSignal.signal_id) ??
        actionableInboxSignal
      );
    }
    const briefingSignals = shell.operatorBriefing?.top_signals ?? [];
    return filterActionableOpenSignals(
      briefingSignals.map((signal) => ({
        signal_id: signal.signal_id,
        title: signal.title,
        status: 'open',
        workspace_id: signal.workspace_id,
        severity: signal.severity,
        summary: signal.summary,
      })),
    )[0];
  }

  async function tryClientHandoff(content: string): Promise<boolean> {
    if (!HANDOFF_CLIENT_RE.test(content)) {
      return false;
    }
    const topSignal = resolveHandoffSignal();
    if (!topSignal) {
      return false;
    }
    await shell.handoffSignalToIde(
      {
        signal_id: topSignal.signal_id,
        workspace_id: topSignal.workspace_id ?? shell.currentWorkspace?.workspace_id ?? '',
        title: topSignal.title,
        summary: topSignal.summary ?? topSignal.title,
      },
      { autoSubmit: true },
    );
    kairoConversationReply.value = 'Handing the top signal off to the IDE.';
    speakReply(kairoConversationReply.value);
    return true;
  }

  async function tryResumeCurrentRun(
    content: string,
    options?: { voiceCaptureMode?: KairoVoiceCaptureMode },
  ): Promise<boolean> {
    if (!DIRECT_CONTINUE_RE.test(content) || HANDOFF_CLIENT_RE.test(content)) {
      return false;
    }
    const run = shell.ideAgentLinkedRun ?? shell.primaryActiveRun;
    if (!run) {
      return false;
    }
    const canContinueAgentRun =
      run.mode === 'agent' && run.phase === 'executing' && !shell.agentStreamActive;
    if (!run.can_resume && !canContinueAgentRun) {
      return false;
    }

    // #region agent log
    fetch('http://127.0.0.1:7852/ingest/0173158c-fd82-46b4-a14c-d55e0685ee25', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'df24bc' },
      body: JSON.stringify({
        sessionId: 'df24bc',
        runId: 'continue-debug',
        hypothesisId: 'H1',
        location: 'use-kairo-conversation.ts:tryResumeCurrentRun',
        message: 'attempting direct run continue',
        data: {
          content,
          runId: run.run_id,
          phase: run.phase,
          canResume: run.can_resume,
          mode: run.mode,
          agentStreamActive: shell.agentStreamActive,
        },
        timestamp: Date.now(),
      }),
    }).catch(() => {});
    // #endregion

    await shell.resumePrimaryRun();
    // #region agent log
    fetch('http://127.0.0.1:7852/ingest/0173158c-fd82-46b4-a14c-d55e0685ee25', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'df24bc' },
      body: JSON.stringify({
        sessionId: 'df24bc',
        runId: 'continue-debug',
        hypothesisId: 'H1',
        location: 'use-kairo-conversation.ts:tryResumeCurrentRun:result',
        message: 'direct run continue finished',
        data: {
          runMutationError: shell.runMutationError ?? '',
          runMutationState: shell.runMutationState,
        },
        timestamp: Date.now(),
      }),
    }).catch(() => {});
    // #endregion
    if (shell.runMutationError) {
      kairoConversationReply.value = shell.runMutationError;
      await deliverVoiceReply(shell.runMutationError, options?.voiceCaptureMode);
      return true;
    }

    kairoConversationReply.value = 'Continuing the current run.';
    await deliverVoiceReply(kairoConversationReply.value, options?.voiceCaptureMode);
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
    lastOperatorPrompt = content;
    const answerTier = determineAnswerTier(content);

    if (CONTINUE_VOICE_RE.test(content)) {
      // #region agent log
      fetch('http://127.0.0.1:7852/ingest/0173158c-fd82-46b4-a14c-d55e0685ee25', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'df24bc' },
        body: JSON.stringify({
          sessionId: 'df24bc',
          runId: 'continue-debug',
          hypothesisId: 'H1',
          location: 'use-kairo-conversation.ts:submitTurn:start',
          message: 'voice continue intent captured',
          data: {
            content,
            voiceCaptureMode: options?.voiceCaptureMode ?? 'none',
            hasPrimaryRun: shell.primaryActiveRun?.run_id ?? '',
            primaryPhase: shell.primaryActiveRun?.phase ?? '',
            primaryCanResume: shell.primaryActiveRun?.can_resume ?? false,
            linkedRun: shell.ideAgentLinkedRun?.run_id ?? '',
          },
          timestamp: Date.now(),
        }),
      }).catch(() => {});
      // #endregion
    }

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
      // Prefer server entity-memory handoff; client inbox top-signal is fallback only.
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
      if (response.action) {
        void executeConverseAction(response.action);
      } else if (shouldAutoDispatchConverseCommand(response)) {
        void shell.submitOperatorCommandContent(response.command_content!);
      }
      if (mentionsBriefingSurfaceOffer(response.reply)) {
        scheduleBriefingSurfaceOffer();
      }
      if (CONTINUE_VOICE_RE.test(content)) {
        // #region agent log
        fetch('http://127.0.0.1:7852/ingest/0173158c-fd82-46b4-a14c-d55e0685ee25', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'df24bc' },
          body: JSON.stringify({
            sessionId: 'df24bc',
            runId: 'continue-debug',
            hypothesisId: 'H1',
            location: 'use-kairo-conversation.ts:submitTurn:response',
            message: 'voice continue intent resolved',
            data: {
              turnKind: response.turn_kind,
              actionType: response.action?.type ?? '',
              requiresConfirmation: response.requires_confirmation ?? null,
              commandContent: response.command_content ?? '',
              replyPreview: String(response.reply || '').slice(0, 160),
            },
            timestamp: Date.now(),
          }),
        }).catch(() => {});
        // #endregion
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
    // Do not fake LISTENING on input focus — that label is reserved for an open mic.
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
    submitTurn,
    handleFocus,
    handleBlur,
    speechCapture,
    startVoiceCapture,
    stopVoiceCapture,
  };
}
