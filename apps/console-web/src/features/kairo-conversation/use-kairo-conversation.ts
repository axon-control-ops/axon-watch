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
  setReportTheaterExecuting,
  setReportTheaterStageIndex,
} from '../report-theater/report-theater-state';
import { pickReportTheaterActions } from '../report-theater/report-theater-model';
import { brainGalaxyConversationFocus } from '../brain-galaxy/brain-galaxy-focus';
import { useKairoSpeechCapture } from './use-kairo-speech-capture';
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

  const canSubmit = computed(
    () =>
      draft.value.trim().length > 0 &&
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
    const raw = normalizeVoiceTranscript((rawContent ?? draft.value).trim());
    if (!raw || pending.value) {
      return;
    }
    const content = expandReportHotword(raw) ?? raw;
    lastOperatorPrompt = content;
    recordSharedKairoHistoryEntry(content);
    const answerTier = determineAnswerTier(content);

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
        shell.interruptKairoVoice();
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
        const narrationToken = reportTheaterSessionToken.value;
        // #region agent log
        fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'bef50e'},body:JSON.stringify({sessionId:'bef50e',runId:'post-fix',hypothesisId:'H7',location:'use-kairo-conversation.ts:report-theater',message:'starting speech-synced report theater narration',data:{token:narrationToken,stageCount:reportTheaterStages.value.length,nextMove:reportTheaterStages.value.at(-1)?.lines?.[0]??null},timestamp:Date.now()})}).catch(()=>{});
        // #endregion
        await narrateReportTheater(reportTheaterStages.value, {
          speak: async (line, speakerName) => {
            // #region agent log
            fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'bef50e'},body:JSON.stringify({sessionId:'bef50e',runId:'post-fix',hypothesisId:'H10',location:'use-kairo-conversation.ts:speak',message:'report theater speak started',data:{token:narrationToken,stageIndex:reportTheaterStageIndex.value,showNextSteps:reportTheaterShowNextSteps.value,linePreview:line.slice(0,140),lineChars:line.length},timestamp:Date.now()})}).catch(()=>{});
            // #endregion
            kairoConversationReply.value = normalizeKairoCopy(line);
            await speakReportTheaterTurn(shell, line, lastOperatorPrompt, speakerName);
            // #region agent log
            fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'bef50e'},body:JSON.stringify({sessionId:'bef50e',runId:'post-fix',hypothesisId:'H10',location:'use-kairo-conversation.ts:speak-done',message:'report theater speak finished',data:{token:narrationToken,stageIndex:reportTheaterStageIndex.value,showNextSteps:reportTheaterShowNextSteps.value,linePreview:line.slice(0,140),lineChars:line.length},timestamp:Date.now()})}).catch(()=>{});
            // #endregion
          },
          setStageIndex: (index) => {
            // #region agent log
            fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'bef50e'},body:JSON.stringify({sessionId:'bef50e',runId:'post-fix',hypothesisId:'H10',location:'use-kairo-conversation.ts:stage',message:'report theater stage shown before speech',data:{index,title:reportTheaterStages.value[index]?.title??null,token:narrationToken},timestamp:Date.now()})}).catch(()=>{});
            // #endregion
            setReportTheaterStageIndex(index);
          },
          onComplete: () => {
            // #region agent log
            fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'bef50e'},body:JSON.stringify({sessionId:'bef50e',runId:'post-fix',hypothesisId:'H11',location:'use-kairo-conversation.ts:complete',message:'report theater directives revealed',data:{token:narrationToken,stageIndex:reportTheaterStageIndex.value},timestamp:Date.now()})}).catch(()=>{});
            // #endregion
            revealReportTheaterNextSteps();
          },
          onCommitted: async () => {
            const directives = buildVaxonReportDirectives({
              nextMove: reportTheaterStages.value.at(-1)?.lines[0] ?? '',
              actions: pickReportTheaterActions(shell.operatorBriefing?.next_safe_actions, 3),
              topSignals: shell.operatorBriefing?.top_signals ?? [],
              workspaces: shell.workspaces,
              readiness: shell.operatorBriefing?.production_readiness ?? null,
            });
            const primary = directives.find((item) => item.kind === 'primary' && item.autoExecute);
            // #region agent log
            fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'bef50e'},body:JSON.stringify({sessionId:'bef50e',runId:'readiness-recovery-fix',hypothesisId:'H51',location:'use-kairo-conversation.ts:auto-commit',message:'VAXON initiative evaluated',data:{token:narrationToken,label:primary?.label??null,autoExecute:Boolean(primary?.autoExecute),actionKind:primary?.briefingAction?.kind??null,signalId:primary?.briefingAction?.signal_id??null,actionTitle:primary?.briefingAction?.title??null,readinessScore:shell.operatorBriefing?.production_readiness?.score??null,blocker:shell.operatorBriefing?.production_readiness?.blockers?.[0]??null},timestamp:Date.now()})}).catch(()=>{});
            // #endregion
            if (!primary?.briefingAction) {
              return;
            }
            setReportTheaterExecuting(true);
            const result = await executeReportTheaterAction(
              shell,
              shell.operatorBriefing,
              primary.briefingAction,
            );
            // #region agent log
            fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'bef50e'},body:JSON.stringify({sessionId:'bef50e',runId:'readiness-recovery-fix',hypothesisId:'H51',location:'use-kairo-conversation.ts:auto-commit:done',message:'VAXON initiative executed',data:{token:narrationToken,ok:result.ok,resultKind:'kind' in result ? result.kind : null,leftSidebar:shell.leftSidebarMode??null,pathname:typeof window!=='undefined'?window.location.pathname:null},timestamp:Date.now()})}).catch(()=>{});
            // #endregion
            if (reportTheaterSessionToken.value === narrationToken) {
              clearQueuedSpokenAlerts();
              clearBriefingSurfaceOffer();
              closeReportTheater();
            }
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
    startVoiceCapture: () => {
      shell.interruptKairoVoice();
      return speechCapture.startCapture();
    },
    stopVoiceCapture: () => speechCapture.stopCapture(),
  };
}
