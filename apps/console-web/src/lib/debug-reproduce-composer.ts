/** Debug Mode Proceed helpers for the agent-dock composer. */

import {
  extractDebugReproduceRequest,
  shouldShowDebugReproduceBanner,
} from './debug-reproduce-view';

export type DebugReproduceComposerMessage = {
  message_id: string;
  role: string;
  content: string;
};

export function isDebugReproduceComposerActive(input: {
  messages: DebugReproduceComposerMessage[];
  streaming: boolean;
  composerMode: string;
  linkedRunMode?: string | null;
  dismissedMessageId: string | null;
}): boolean {
  const request = extractDebugReproduceRequest({
    messages: input.messages,
    streaming: input.streaming,
  });
  return shouldShowDebugReproduceBanner({
    composerMode: input.composerMode,
    linkedRunMode: input.linkedRunMode,
    request,
    dismissedMessageId: input.dismissedMessageId,
  });
}

export function activeDebugReproduceMessageId(input: {
  messages: DebugReproduceComposerMessage[];
  streaming: boolean;
}): string | null {
  return (
    extractDebugReproduceRequest({
      messages: input.messages,
      streaming: input.streaming,
    })?.messageId ?? null
  );
}
