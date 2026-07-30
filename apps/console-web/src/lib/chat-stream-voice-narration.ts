import type { KairoNarrationLevel } from '../contracts/canonical';

import { narrationForCompletion, isProgressOrIntentSentence } from './kairo-agent-narration';
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
  sanitizeAgentThinkingForOperator,
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
import { dropWaitingKairoNarration, stopActiveKairoNarration } from './kairo-voice-queue';
import type { KairoVoiceSpeaker } from './kairo-voice-utterance';

type Narrator = ReturnType<typeof createKairoAgentMilestoneNarrator>;
type ProgressNarrator = ReturnType<typeof createKairoProgressNarrator>;

export type ChatStreamVoiceNarration = {
  toolNarrationEnabled: boolean;
  progressNarrator: ProgressNarrator | null;
  agentMilestoneNarrator: Narrator | null;
  answerNarrator: Narrator | null;
  /** Reserved: start bookend is model-only (no canned UI ack). */
  speakStartBookend: () => boolean;
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
  speaker?: () => KairoVoiceSpeaker | null | undefined;
}): ChatStreamVoiceNarration {
  const toolNarrationEnabled = isToolCapableComposerMode(input.composerMode);
  const answerMode = isAnswerNarrationComposerMode(input.composerMode);
  const thinkingThrottle = createKairoThinkingSpeechThrottle();
  const toolThrottle = createKairoIntervalThrottle({ intervalMs: TOOL_MILESTONE_INTERVAL_MS });
  const azureVoiceId = input.azureVoiceId;
  const speaker = input.speaker;
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
        speaker,
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
        speaker,
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
        speaker,
      })
    : null;

  function cancelStaleNarration(): void {
    agentMilestoneNarrator?.cancel();
    progressNarrator?.cancel();
    dropWaitingKairoNarration('stale_run_advance');
  }

  /** Stream ended — never leave mid-run intent TTS playing after Done/ask. */
  function clearMidRunSpeechForStreamEnd(): void {
    agentMilestoneNarrator?.cancel();
    progressNarrator?.cancel();
    stopActiveKairoNarration('stream_complete');
  }

  function speakVerbatimStart(line: string): boolean {
    const message = line.trim();
    if (
      !toolNarrationEnabled ||
      !message ||
      thinkingThrottle.spokenCount() > 0 ||
      input.narration() === 'off' ||
      !input.voiceDeliveryAllowed()
    ) {
      return false;
    }
    cancelStaleNarration();
    agentMilestoneNarrator?.narrate({
      key: 'start',
      message,
      verbatim: true,
    });
    thinkingThrottle.recordSpoken();
    thinkingCarriesUpdate = true;
    lastSpokenThinking = message;
    return true;
  }

  function speakStartBookend(): boolean {
    // No canned ack — wait for the model's first live thinking/reply line.
    return false;
  }

  function maybeSpeakThinkingBlock(spokenBlock: string): boolean {
    if (!toolNarrationEnabled) {
      return false;
    }
    const cleaned = sanitizeAgentThinkingForOperator(spokenBlock, {
      speakerName: speaker?.()?.name ?? null,
    });
    // First breath: only real model text — never a console template.
    if (thinkingThrottle.spokenCount() === 0) {
      return cleaned ? speakVerbatimStart(cleaned) : false;
    }
    if (!cleaned) {
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
      return false;
    }
    cancelStaleNarration();
    agentMilestoneNarrator?.narrate({
      key: `thinking:${thinkingThrottle.spokenCount()}`,
      message: cleaned,
      verbatim: true,
    });
    thinkingThrottle.recordSpoken();
    thinkingCarriesUpdate = true;
    lastSpokenThinking = cleaned;
    if (waitProgress) {
      spokeWaitProgress = true;
    }
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
      // Always drain mid-run TTS first so "I am checking…" cannot speak after Done/ask.
      clearMidRunSpeechForStreamEnd();
      // Thinking already carried the "what I'll do" plan mid-run. Do not re-speak a
      // progress opener after the roster is IDLE — unless this is an ask/reproduce cue.
      if (
        completion.key === 'done' &&
        thinkingCarriesUpdate &&
        !completion.verbatim &&
        (isProgressOrIntentSentence(completion.message) ||
          completion.message === 'Done' ||
          completion.message === 'Shift complete.')
      ) {
        return;
      }
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
    answerNarrator?.cancel();
    stopActiveKairoNarration('stream_complete');
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
      clearMidRunSpeechForStreamEnd();
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
    answerNarrator?.cancel();
    stopActiveKairoNarration('stream_complete');
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
    speakStartBookend,
    maybeSpeakThinkingBlock,
    narrateAgentMilestone,
    narrateProgress,
    narrateCompletion,
    narrateFailure,
  };
}
