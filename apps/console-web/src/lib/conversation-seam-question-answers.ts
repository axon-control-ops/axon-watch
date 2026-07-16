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

export function answeredOptionForQuestion(
  items: ConversationDisplayItem[],
  messageId: string,
  prompt: string,
  options: AgentQuestionOption[],
  itemIndex: number,
): AgentQuestionOption | null {
  const followupText = nextUserMessageContent(items, itemIndex);
  const matchOptions = withOtherQuestionOption(options);
  if (isQuestionMarkedAnswered(messageId, prompt)) {
    const fromFollowup = matchQuestionAnswerFromUserText(matchOptions, followupText);
    if (fromFollowup) {
      return fromFollowup;
    }
    const followup = followupText.trim();
    if (followup) {
      return matchQuestionAnswerFromUserText(matchOptions, followup) ?? matchOptions[0] ?? null;
    }
  }
  return matchQuestionAnswerFromUserText(matchOptions, followupText);
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
