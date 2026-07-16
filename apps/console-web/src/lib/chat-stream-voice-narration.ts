import type { KairoNarrationLevel } from '../contracts/canonical';

import { narrationForCompletion } from './kairo-agent-narration';
import { createKairoAgentMilestoneNarrator } from './kairo-agent-milestone-narrator';
import {
  isAnswerNarrationComposerMode,
  shouldNarrateAnswerCompletion,
} from './composer-answer-narration';
import { isToolCapableComposerMode } from './composer-tool-modes';
import { createKairoProgressNarrator } from './kairo-progress-narrator';
import { shouldSpeakLiveThinkingBlock } from './kairo-narration-policy';

type Narrator = ReturnType<typeof createKairoAgentMilestoneNarrator>;
type ProgressNarrator = ReturnType<typeof createKairoProgressNarrator>;

export type ChatStreamVoiceNarration = {
  toolNarrationEnabled: boolean;
  progressNarrator: ProgressNarrator | null;
  agentMilestoneNarrator: Narrator | null;
  answerNarrator: Narrator | null;
  maybeSpeakStartIntent: (spokenBlock: string, spokenStartIntent: boolean) => boolean;
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
  voiceDeliveryAllowed: () => boolean;
  operatorPrompt: () => string;
  fullAccess: () => boolean;
}): ChatStreamVoiceNarration {
  const toolNarrationEnabled = isToolCapableComposerMode(input.composerMode);
  const answerMode = isAnswerNarrationComposerMode(input.composerMode);

  const progressNarrator = toolNarrationEnabled
    ? createKairoProgressNarrator({
        messageId: input.messageId,
        sessionId: input.sessionId,
        workspaceId: input.workspaceId,
        narration: input.narration,
        voiceDeliveryAllowed: input.voiceDeliveryAllowed,
      })
    : null;

  const agentMilestoneNarrator = toolNarrationEnabled
    ? createKairoAgentMilestoneNarrator({
        messageId: input.messageId,
        sessionId: input.sessionId,
        workspaceId: input.workspaceId,
        narration: input.narration,
        voiceDeliveryAllowed: input.voiceDeliveryAllowed,
        operatorPrompt: input.operatorPrompt,
        fullAccess: input.fullAccess,
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
      })
    : null;

  function maybeSpeakStartIntent(spokenBlock: string, spokenStartIntent: boolean): boolean {
    if (
      !toolNarrationEnabled ||
      spokenStartIntent ||
      !spokenBlock ||
      !shouldSpeakLiveThinkingBlock({
        narration: input.narration(),
        spokenBlock,
      })
    ) {
      return false;
    }
    agentMilestoneNarrator?.narrate({
      key: 'start',
      message: spokenBlock,
      verbatim: true,
    });
    return true;
  }

  function narrateProgress(payload: {
    event_key?: string;
    event_type?: string;
    context?: Record<string, unknown>;
  }): void {
    if (!toolNarrationEnabled || !payload.event_key || !payload.event_type) {
      return;
    }
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
    // Ask/Plan: final answer only, never tool/edit/thinking milestones.
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
    maybeSpeakStartIntent,
    narrateProgress,
    narrateCompletion,
    narrateFailure,
  };
}
