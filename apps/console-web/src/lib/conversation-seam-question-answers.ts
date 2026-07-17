import type { Ref } from 'vue';

import type { AgentQuestionOption } from '../lib/agent-question-view';
import { withOtherQuestionOption } from '../lib/agent-question-view';
import {
  isQuestionMarkedAnswered,
  matchQuestionAnswerFromUserText,
} from '../lib/answered-agent-questions';

type ConversationDisplayItem = {
  kind: string;
  message?: { role: string; content?: string };
};

export function nextUserMessageContent(
  items: ConversationDisplayItem[],
  fromIndex: number,
): string {
  for (let index = fromIndex + 1; index < items.length; index += 1) {
    const entry = items[index];
    if (entry?.kind === 'message' && entry.message?.role === 'operator') {
      return entry.message.content ?? '';
    }
    if (entry?.kind === 'message' && entry.message?.role === 'agent') {
      break;
    }
  }
  return '';
}

/** True when a user follow-up is clearly answering this specific ask prompt. */
export function followupCitesQuestionPrompt(followupText: string, prompt: string): boolean {
  const text = String(followupText || '').trim();
  const trimmedPrompt = String(prompt || '').trim();
  if (!text || !trimmedPrompt) {
    return false;
  }
  const answerTo = `(answer to: ${trimmedPrompt})`;
  if (text.includes(answerTo)) {
    return true;
  }
  // Tolerate minor whitespace differences in the answer-to trailer.
  const loose = text.match(/\(answer to:\s*([\s\S]*?)\)\s*$/i);
  if (loose?.[1]?.trim() === trimmedPrompt) {
    return true;
  }
  return false;
}

export function answeredOptionForQuestion(
  items: ConversationDisplayItem[],
  messageId: string,
  prompt: string,
  options: AgentQuestionOption[],
  itemIndex: number,
): AgentQuestionOption | null {
  const followupText = nextUserMessageContent(items, itemIndex);
  const matchOptions = withOtherQuestionOption(options);
  const marked = isQuestionMarkedAnswered(messageId, prompt);
  const citesThisPrompt = followupCitesQuestionPrompt(followupText, prompt);

  // Never let one card's "Selected option 1" collapse every other ask card.
  if (!marked && !citesThisPrompt) {
    return null;
  }

  const matched = matchQuestionAnswerFromUserText(matchOptions, followupText);
  if (matched) {
    return matched;
  }

  if (marked) {
    const followup = followupText.trim();
    if (followup) {
      return matchOptions[0] ?? null;
    }
  }

  return null;
}

export type ConversationSeamAnswerBridge = {
  conversationDisplayItems: Ref<ConversationDisplayItem[]>;
  answeredOptionForQuestion: (
    messageId: string,
    prompt: string,
    options: AgentQuestionOption[],
    itemIndex: number,
  ) => AgentQuestionOption | null;
};

export function createConversationSeamAnswerBridge(
  conversationDisplayItems: Ref<ConversationDisplayItem[]>,
): ConversationSeamAnswerBridge {
  return {
    conversationDisplayItems,
    answeredOptionForQuestion(messageId, prompt, options, itemIndex) {
      return answeredOptionForQuestion(
        conversationDisplayItems.value,
        messageId,
        prompt,
        options,
        itemIndex,
      );
    },
  };
}
