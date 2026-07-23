import type { KairoNarrationLevel } from '../contracts/canonical';

import { narrationForCompletion } from './kairo-agent-narration';
import type { NarrationMilestone } from './kairo-agent-narration';
import { createKairoAgentMilestoneNarrator } from './kairo-agent-milestone-narrator';
import {
  isAnswerNarrationComposerMode,
  shouldNarrateAnswerCompletion,
} from './composer-answer-narration';
import { isToolCapableComposerMode } from './composer-tool-modes';
import { createKairoProgressNarrator } from './kairo-progress-narrator';
import {
  isWaitProgressThinking,
  stripAgentStreamFenceMarkers,
  thinkingSpeechSimilarity,
} from './agent-live-line-view';
import {
  shouldNarrateAgentEvent,
  shouldSpeakLiveThinkingBlock,
} from './kairo-narration-policy';
import {
  createKairoIntervalThrottle,
  createKairoThinkingSpeechThrottle,
  TOOL_MILESTONE_INTERVAL_MS,
} from './kairo-narration-throttle';
import { dropWaitingKairoNarration } from './kairo-voice-queue';

type Narrator = ReturnType<typeof createKairoAgentMilestoneNarrator>;
type ProgressNarrator = ReturnType<typeof createKairoProgressNarrator>;

export type ChatStreamVoiceNarration = {
  toolNarrationEnabled: boolean;
  progressNarrator: ProgressNarrator | null;
  agentMilestoneNarrator: Narrator | null;
  answerNarrator: Narrator | null;
  maybeSpeakThinkingBlock: (spokenBlock: string) => boolean;
  narrateAgentMilestone: (
    milestone: NarrationMilestone,
    options?: { preserveQueue?: boolean },
  ) => void;
  narrateProgress: (payload: {
    event_key?: string;
    event_type?: string;
    context?: Record<string, unknown>;
  }) => void;
  narrateCompletion: (finalContent: string) => void;
  narrateFailure: (streamedContent: string, message: string) => void;
};

export function createChatStreamVoiceNarration(input: {
  composerMode: string | null | undefined;
  messageId: string;
  sessionId: () => string;
  workspaceId: () => string;
  narration: () => KairoNarrationLevel;
  narrateToolProgress: () => boolean;
  voiceDeliveryAllowed: () => boolean;
  operatorPrompt: () => string;
  fullAccess: () => boolean;
  azureVoiceId?: () => string | null | undefined;
}): ChatStreamVoiceNarration {
  const toolNarrationEnabled = isToolCapableComposerMode(input.composerMode);
  const answerMode = isAnswerNarrationComposerMode(input.composerMode);
  const thinkingThrottle = createKairoThinkingSpeechThrottle();
  const toolThrottle = createKairoIntervalThrottle({ intervalMs: TOOL_MILESTONE_INTERVAL_MS });
  const azureVoiceId = input.azureVoiceId;
  /** Once live thinking speaks, prefer it over canned tool/edit lines for this turn. */
  let thinkingCarriesUpdate = false;
  let lastSpokenThinking = '';
  let spokeWaitProgress = false;

  const progressNarrator = toolNarrationEnabled
    ? createKairoProgressNarrator({
        messageId: input.messageId,
        sessionId: input.sessionId,
        workspaceId: input.workspaceId,
        narration: input.narration,
        voiceDeliveryAllowed: input.voiceDeliveryAllowed,
        azureVoiceId,
      })
    : null;

  const agentMilestoneNarrator = toolNarrationEnabled
    ? createKairoAgentMilestoneNarrator({
        messageId: input.messageId,
        sessionId: input.sessionId,
        workspaceId: input.workspaceId,
        narration: input.narration,
        narrateToolProgress: input.narrateToolProgress,
        voiceDeliveryAllowed: input.voiceDeliveryAllowed,
        operatorPrompt: input.operatorPrompt,
        fullAccess: input.fullAccess,
        azureVoiceId,
      })
    : null;

  const answerNarrator = answerMode
    ? createKairoAgentMilestoneNarrator({
        messageId: input.messageId,
        sessionId: input.sessionId,
        workspaceId: input.workspaceId,
        narration: input.narration,
        voiceDeliveryAllowed: input.voiceDeliveryAllowed,
        operatorPrompt: input.operatorPrompt,
        fullAccess: input.fullAccess,
        azureVoiceId,
      })
    : null;

  function cancelStaleNarration(): void {
    agentMilestoneNarrator?.cancel();
    progressNarrator?.cancel();
    dropWaitingKairoNarration('stale_run_advance');
  }

  function maybeSpeakThinkingBlock(spokenBlock: string): boolean {
    const cleaned = stripAgentStreamFenceMarkers(spokenBlock);
    if (!toolNarrationEnabled || !cleaned) {
      return false;
    }
    const waitProgress = isWaitProgressThinking(cleaned);
    const similarity = lastSpokenThinking
      ? thinkingSpeechSimilarity(lastSpokenThinking, cleaned)
      : 0;
    if (
      !shouldSpeakLiveThinkingBlock({
        narration: input.narration(),
        spokenBlock: cleaned,
        lastSpokenBlock: lastSpokenThinking || null,
        alreadySpokeWaitProgress: spokeWaitProgress,
        isWaitProgress: waitProgress,
        similarityToLast: similarity,
      }) ||
      !thinkingThrottle.canSpeak() ||
      !input.voiceDeliveryAllowed()
    ) {
      // #region agent log
      fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'fc0b35'},body:JSON.stringify({sessionId:'fc0b35',runId:'post-fix',hypothesisId:'H2',location:'chat-stream-voice-narration.ts:maybeSpeakThinkingBlock',message:'thinking speech skipped',data:{preview:cleaned.slice(0,100),waitProgress,spokeWaitProgress,similarity,hasFence:/:::/.test(spokenBlock)},timestamp:Date.now()})}).catch(()=>{});
      // #endregion
      return false;
    }
    cancelStaleNarration();
    const milestoneKey =
      thinkingThrottle.spokenCount() === 0 ? 'start' : `thinking:${thinkingThrottle.spokenCount()}`;
    agentMilestoneNarrator?.narrate({
      key: milestoneKey,
      message: cleaned,
      verbatim: true,
    });
    thinkingThrottle.recordSpoken();
    thinkingCarriesUpdate = true;
    lastSpokenThinking = cleaned;
    if (waitProgress) {
      spokeWaitProgress = true;
    }
    // #region agent log
    fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'fc0b35'},body:JSON.stringify({sessionId:'fc0b35',runId:'post-fix',hypothesisId:'H1-H2',location:'chat-stream-voice-narration.ts:maybeSpeakThinkingBlock',message:'live thinking spoken — tools will defer',data:{preview:cleaned.slice(0,100),spokenCount:thinkingThrottle.spokenCount(),waitProgress,spokeWaitProgress,hasFence:/:::/.test(cleaned)},timestamp:Date.now()})}).catch(()=>{});
    // #endregion
    return true;
  }

  function narrateAgentMilestone(
    milestone: NarrationMilestone,
    options?: { preserveQueue?: boolean },
  ): void {
    if (!toolNarrationEnabled) {
      return;
    }
    const narration = input.narration();
    if (
      !shouldNarrateAgentEvent({
        eventKey: milestone.key,
        narration,
        narrateToolProgress: input.narrateToolProgress(),
        thinkingCarriesUpdate,
      })
    ) {
      // #region agent log
      if (milestone.key.startsWith('tool:') || milestone.key.startsWith('edit:')) {
        fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'fc0b35'},body:JSON.stringify({sessionId:'fc0b35',runId:'agent-aware-speech',hypothesisId:'H-skip-tool',location:'chat-stream-voice-narration.ts:narrateAgentMilestone',message:'skipped canned tool/edit milestone',data:{key:milestone.key,toolLabel:milestone.toolLabel??null,thinkingCarriesUpdate,narration},timestamp:Date.now()})}).catch(()=>{});
      }
      // #endregion
      return;
    }
    if (milestone.key.startsWith('tool:') && !toolThrottle.canSpeak()) {
      return;
    }
    if (!options?.preserveQueue) {
      cancelStaleNarration();
    }
    agentMilestoneNarrator?.narrate(milestone);
    if (milestone.key.startsWith('tool:')) {
      toolThrottle.recordSpoken();
      // #region agent log
      fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'fc0b35'},body:JSON.stringify({sessionId:'fc0b35',runId:'agent-aware-speech',hypothesisId:'H-tool',location:'chat-stream-voice-narration.ts:narrateAgentMilestone',message:'speaking tool milestone',data:{key:milestone.key,toolLabel:milestone.toolLabel??null,messagePreview:(milestone.message??'').slice(0,100)},timestamp:Date.now()})}).catch(()=>{});
      // #endregion
    }
  }

  function narrateProgress(payload: {
    event_key?: string;
    event_type?: string;
    context?: Record<string, unknown>;
  }): void {
    if (!toolNarrationEnabled || !payload.event_key || !payload.event_type) {
      return;
    }
    cancelStaleNarration();
    progressNarrator?.narrate({
      eventKey: payload.event_key,
      eventType: payload.event_type,
      context: {
        operator_prompt: input.operatorPrompt(),
        ...(payload.context ?? {}),
      },
    });
  }

  function narrateCompletion(finalContent: string): void {
    const completion = narrationForCompletion(finalContent);
    if (toolNarrationEnabled) {
      cancelStaleNarration();
      agentMilestoneNarrator?.narrate(completion);
      return;
    }
    if (
      !shouldNarrateAnswerCompletion({
        mode: input.composerMode,
        narration: input.narration(),
      }) ||
      !input.voiceDeliveryAllowed()
    ) {
      return;
    }
    answerNarrator?.narrate({
      ...completion,
      verbatim: true,
    });
  }

  function narrateFailure(streamedContent: string, message: string): void {
    const errorSummary = message.trim().slice(0, 120);
    const failureContent = streamedContent || message;
    const completion = narrationForCompletion(failureContent);
    const failure =
      completion.key === 'failed'
        ? { ...completion, message: errorSummary || completion.message }
        : { key: 'failed' as const, message: errorSummary || 'Failed' };

    if (toolNarrationEnabled) {
      cancelStaleNarration();
      agentMilestoneNarrator?.narrate(failure);
      return;
    }
    if (
      !shouldNarrateAnswerCompletion({
        mode: input.composerMode,
        narration: input.narration(),
      }) ||
      !input.voiceDeliveryAllowed()
    ) {
      return;
    }
    answerNarrator?.narrate({
      ...failure,
      verbatim: true,
    });
  }

  return {
    toolNarrationEnabled,
    progressNarrator,
    agentMilestoneNarrator,
    answerNarrator,
    maybeSpeakThinkingBlock,
    narrateAgentMilestone,
    narrateProgress,
    narrateCompletion,
    narrateFailure,
  };
}
