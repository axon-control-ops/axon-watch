import { computed, onBeforeUnmount } from 'vue';

import { postKairoConverse } from '../../lib/kairo-converse-client';
import { parseChatUiAction } from '../../lib/chat-ui-action';
import {
  handleKairoComposerHistoryKeydown,
  recordSharedKairoHistoryEntry,
  sharedKairoDraft,
  sharedKairoPending,
  sharedKairoThinkingLine,
  wireSharedKairoDraftPersistence,
} from '../../lib/kairo-conversation-shared-session';
import { normalizeKairoCopy, normalizeVoiceTranscript } from '../../lib/kairo-entity-labels';
import { recordOperatorArtifacts } from '../../lib/operator-artifact-view';
import {
  formatConversationDisplayReply,
  sanitizeSpokenReply,
} from '../../lib/sanitize-spoken-reply';
import { clearQueuedSpokenAlerts } from '../../lib/spoken-alert-delivery';
import {
  clearKairoVoiceFollowupWindow,
  finalizeKairoVoiceFollowupWindow,
  scheduleKairoVoiceFollowupWindowAfterSpeech,
} from '../../lib/kairo-voice-followup-window';
import type { KairoVoiceCaptureMode } from '../../lib/kairo-voice-gate';
import { useShellStore } from '../../stores/shell';
import { handleConversationModelSwitchIntent } from './conversation-model-switch-handler';
import {
  applyKairoConversationNavigationIntent,
  resolveKairoConversationNavigationIntent,
} from './conversation-navigation-handler';
import { expandReportHotword } from './conversation-report-hotword';
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
import { executeReportTheaterAction } from '../report-theater/report-theater-execute';
import {
  buildVaxonReportDirectives,
} from '../report-theater/report-theater-directives';
import { narrateReportTheater } from '../report-theater/report-theater-narration';
import { speakReportTheaterTurn } from '../report-theater/report-theater-speaker';
import {
  closeReportTheater,
  openReportTheater,
  reportTheaterSessionToken,
  reportTheaterShowNextSteps,
  reportTheaterStageIndex,
  reportTheaterStages,
  revealReportTheaterNextSteps,
  setReportTheaterDirectives,
  setReportTheaterExecuting,
  setReportTheaterStageIndex,
} from '../report-theater/report-theater-state';
import { pickReportTheaterActions } from '../report-theater/report-theater-model';
import { brainGalaxyConversationFocus } from '../brain-galaxy/brain-galaxy-focus';
import { useKairoSpeechCapture } from './use-kairo-speech-capture';
import { useVaxonConversationAttachments } from './use-vaxon-conversation-attachments';
import {
  uploadVaxonConverseAttachments,
  vaxonConversePromptForAttachments,
} from './upload-vaxon-converse-attachments';
import {
  createKairoConversationTurnHandlers,
  HANDOFF_CLIENT_RE,
} from './kairo-conversation-turn-handlers';
import {
  createKairoRuntimeAssistantCue,
  createKairoVoiceDelivery,
} from './kairo-conversation-voice-runtime';

export function useKairoConversation() {
  const shell = useShellStore();
  wireSharedKairoDraftPersistence(shell);
  const draft = sharedKairoDraft;
  const pending = sharedKairoPending;
  const thinkingLine = sharedKairoThinkingLine;
  let lastOperatorPrompt = '';
  const attachments = useVaxonConversationAttachments();

  const canSubmit = computed(
    () =>
      (draft.value.trim().length > 0 || attachments.pendingAttachments.value.length > 0) &&
      !pending.value &&
      kairoConversationPhase.value !== 'thinking',
  );
  const workspaceId = computed(() => shell.currentWorkspace?.workspace_id ?? '');

  const speechCapture = useKairoSpeechCapture({
    privacyBlocked: () => shell.operatorPresenceSettings.privacy_mode,
    sttMode: () => shell.operatorPresenceSettings.stt_mode,
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

  function resetDraftState(): void {
    draft.value = '';
    pending.value = false;
    thinkingLine.value = '';
    attachments.clearAttachments();
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

  async function submitTurn(
    rawContent?: string,
    options?: { voiceCaptureMode?: KairoVoiceCaptureMode },
  ): Promise<void> {
    const pendingFiles = [...attachments.pendingAttachments.value];
    const raw = normalizeVoiceTranscript(
      vaxonConversePromptForAttachments(rawContent ?? draft.value, pendingFiles.length),
    );
    if (!raw || pending.value) {
      return;
    }
    const content = expandReportHotword(raw) ?? raw;
    lastOperatorPrompt = content;
    recordSharedKairoHistoryEntry(content);
    const answerTier = pendingFiles.length
      ? 'deep'
      : determineAnswerTier(content);

    pending.value = true;
    kairoConversationError.value = null;
    thinkingLine.value = thinkingStatusLine(content, answerTier);
    clearKairoVoiceFollowupWindow();
    setKairoConversationPhase('thinking');
    if (answerTier === 'deep') {
      scheduleRuntimeAssistantCue(content);
    }

    const modelHandled = await handleConversationModelSwitchIntent({
      shell,
      content,
      voiceCaptureMode: options?.voiceCaptureMode,
      clearRuntimeAssistantCue,
      deliverVoiceReply,
      resetDraftState,
    });
    if (modelHandled) {
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
        resetDraftState,
      });
      return;
    }

    if (await tryBriefingSurfaceFollowup(content, options)) {
      clearRuntimeAssistantCue();
      return;
    }
    if (await tryResumeCurrentRun(content, options)) {
      clearRuntimeAssistantCue();
      resetDraftState();
      return;
    }

    try {
      const attachmentIds = pendingFiles.length
        ? await uploadVaxonConverseAttachments(workspaceId.value, pendingFiles)
        : [];
      const response = await postKairoConverse({
        content,
        session_id: kairoSpeechSessionId(),
        workspace_id: workspaceId.value,
        use_runtime: answerTier === 'deep' || attachmentIds.length > 0,
        answer_tier: answerTier,
        context_workspace_id: brainGalaxyConversationFocus.value?.workspaceId ?? workspaceId.value,
        context_signal_id: brainGalaxyConversationFocus.value?.signalId ?? '',
        context_node_id: brainGalaxyConversationFocus.value?.nodeId ?? '',
        attachment_ids: attachmentIds.length ? attachmentIds : undefined,
      });
      clearRuntimeAssistantCue();
      if (response.artifacts.length) {
        recordOperatorArtifacts(response.artifacts, parseChatUiAction);
      }
      if (!response.action && HANDOFF_CLIENT_RE.test(content)) {
        if (await tryClientHandoff(content)) {
          resetDraftState();
          return;
        }
      }
      kairoConversationReply.value = normalizeKairoCopy(
        formatConversationDisplayReply(response.reply) || sanitizeSpokenReply(response.reply),
      );
      resetDraftState();
      await dispatchKairoConverseOutcome(shell, response, executeConverseAction);
      if (response.dispatch_lane === 'deterministic_report') {
        await shell.interruptKairoVoiceAndWait();
        clearQueuedSpokenAlerts();
        openReportTheater({
          sections: {
            attention: response.report?.sections?.attention ?? [],
            work_in_flight: response.report?.sections?.work_in_flight ?? [],
            lead_rollups: response.report?.sections?.lead_rollups ?? [],
            fleet: response.report?.sections?.fleet ?? [],
            next_move: response.report?.sections?.next_move ?? '',
          },
          fingerprint: response.report?.fingerprint ?? null,
          reply: response.reply,
          spokenReply: response.spoken_reply,
        });
        const committedDirectives = buildVaxonReportDirectives({
          nextMove: reportTheaterStages.value.at(-1)?.lines[0] ?? '',
          actions: pickReportTheaterActions(shell.operatorBriefing?.next_safe_actions, 3),
          topSignals: shell.operatorBriefing?.top_signals ?? [],
          workspaces: shell.workspaces,
          readiness: shell.operatorBriefing?.production_readiness ?? null,
        });
        setReportTheaterDirectives(committedDirectives);
        const narrationToken = reportTheaterSessionToken.value;
        await narrateReportTheater(reportTheaterStages.value, {
          speak: async (line, speakerName, onPlaybackStart) => {
            await speakReportTheaterTurn(
              shell,
              line,
              lastOperatorPrompt,
              speakerName,
              () => {
                kairoConversationReply.value = normalizeKairoCopy(line);
                onPlaybackStart?.();
              },
            );
          },
          setStageIndex: (index) => {
            setReportTheaterStageIndex(index);
          },
          onComplete: () => {
            revealReportTheaterNextSteps();
          },
          onCommitted: async () => {
            const primary = committedDirectives.find((item) => item.kind === 'primary');
            // #region agent log
            fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'bef50e'},body:JSON.stringify({sessionId:'bef50e',runId:'post-fix-route-sync',hypothesisId:'R1',location:'use-kairo-conversation.ts:onCommitted:frozen',message:'executing frozen displayed directive',data:{primaryLabel:primary?.label??null,actionKind:primary?.briefingAction?.kind??null,workspaceId:primary?.briefingAction?.workspace_id??null,currentReadiness:shell.operatorBriefing?.production_readiness?.score??null},timestamp:Date.now()})}).catch(()=>{});
            // #endregion
            if (!primary?.briefingAction) {
              // #region agent log
              fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'bef50e'},body:JSON.stringify({sessionId:'bef50e',runId:'standup-voice',hypothesisId:'D1',location:'use-kairo-conversation.ts:onCommitted',message:'stand-up commitment had no bound action',data:{primaryLabel:primary?.label??null,autoExecute:primary?.autoExecute??null},timestamp:Date.now()})}).catch(()=>{});
              // #endregion
              return;
            }
            // Auto-commit: execute immediately — do not add another spoken turn.
            if (primary.autoExecute) {
              // #region agent log
              fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'bef50e'},body:JSON.stringify({sessionId:'bef50e',runId:'standup-voice',hypothesisId:'D2',location:'use-kairo-conversation.ts:autoExecute',message:'auto-executing stand-up primary directive',data:{primaryLabel:primary.label,actionKind:primary.briefingAction.kind,workspaceId:primary.briefingAction.workspace_id??null,signalId:primary.briefingAction.signal_id??null},timestamp:Date.now()})}).catch(()=>{});
              // #endregion
              setReportTheaterExecuting(true);
              await executeReportTheaterAction(
                shell,
                shell.operatorBriefing,
                primary.briefingAction,
              );
              if (reportTheaterSessionToken.value === narrationToken) {
                clearQueuedSpokenAlerts();
                clearBriefingSurfaceOffer();
                closeReportTheater();
              }
              return;
            }
            const secondary = committedDirectives.find((item) => item.kind !== 'primary');
            const choiceLine = secondary
              ? `Your call. ${primary.label}. Or ${secondary.label}.`
              : `Your call. ${primary.label}.`;
            // #region agent log
            fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'bef50e'},body:JSON.stringify({sessionId:'bef50e',runId:'standup-voice',hypothesisId:'S2',location:'use-kairo-conversation.ts:directive-voice',message:'speaking stand-up directive choice',data:{primaryLabel:primary.label,secondaryLabel:secondary?.label??null,autoExecute:false,linePreview:choiceLine.slice(0,160)},timestamp:Date.now()})}).catch(()=>{});
            // #endregion
            kairoConversationReply.value = normalizeKairoCopy(choiceLine);
            await speakReportTheaterTurn(shell, choiceLine, lastOperatorPrompt);
          },
          isCancelled: () => reportTheaterSessionToken.value !== narrationToken,
        });
        if (options?.voiceCaptureMode === 'hands_free') {
          scheduleKairoVoiceFollowupWindowAfterSpeech();
          finalizeKairoVoiceFollowupWindow();
        }
      } else {
        if (mentionsBriefingSurfaceOffer(response.reply)) {
          scheduleBriefingSurfaceOffer();
        }
        await deliverVoiceReply(response.reply, options?.voiceCaptureMode, {
          spokenReply: response.spoken_reply,
        });
      }
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
    handleHistoryKeydown: handleKairoComposerHistoryKeydown,
    speechCapture,
    attachments,
    startVoiceCapture: () => {
      shell.interruptKairoVoice();
      return speechCapture.startCapture();
    },
    stopVoiceCapture: () => speechCapture.stopCapture(),
  };
}
