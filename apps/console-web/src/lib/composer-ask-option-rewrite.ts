import {
  formatQuestionAnswer,
  withOtherQuestionOption,
  type AgentQuestionOption,
} from './agent-question-view';
import { isQuestionMarkedAnswered, matchQuestionAnswerFromUserText } from './answered-agent-questions';
import { parseAgentTranscriptBlocks } from './agent-transcript-blocks';

export type PendingAskQuestion = {
  messageId: string;
  prompt: string;
  options: AgentQuestionOption[];
};

/** Latest unanswered ask card in the thread (last question segment of the last agent message). */
export function latestUnansweredAskFromMessages(
  messages: ReadonlyArray<{ message_id?: string; role?: string; content?: string }>,
): PendingAskQuestion | null {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (message?.role !== 'agent') {
      continue;
    }
    const messageId = String(message.message_id ?? '').trim();
    if (!messageId) {
      return null;
    }
    const questions = parseAgentTranscriptBlocks(message.content ?? '').filter(
      (
        segment,
      ): segment is Extract<typeof segment, { kind: 'question' } | { kind: 'lead-checkin' }> =>
        segment.kind === 'question' || segment.kind === 'lead-checkin',
    );
    for (let q = questions.length - 1; q >= 0; q -= 1) {
      const question = questions[q];
      if (!question || isQuestionMarkedAnswered(messageId, question.prompt)) {
        continue;
      }
      return {
        messageId,
        prompt: question.prompt,
        options: withOtherQuestionOption(question.options),
      };
    }
    // Older agent turns are not candidates once we hit any agent message.
    return null;
  }
  return null;
}

/**
 * When the operator types a bare option id ("3") against an open ask card,
 * rewrite to the same Continue payload the card would send.
 */
export function rewriteComposerAskOptionAnswer(
  draft: string,
  messages: ReadonlyArray<{ message_id?: string; role?: string; content?: string }>,
): { content: string; ask: PendingAskQuestion; option: AgentQuestionOption } | null {
  const trimmed = String(draft || '').trim();
  if (!/^\d+$/.test(trimmed)) {
    return null;
  }
  const ask = latestUnansweredAskFromMessages(messages);
  if (!ask) {
    return null;
  }
  const option = matchQuestionAnswerFromUserText(ask.options, trimmed);
  if (!option) {
    return null;
  }
  return {
    content: formatQuestionAnswer(option, ask.prompt),
    ask,
    option,
  };
}
