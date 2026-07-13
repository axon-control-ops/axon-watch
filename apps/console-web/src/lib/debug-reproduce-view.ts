/** Cursor-style Debug Mode: parse reproduce pauses and build the proceed follow-up. */

import { parseAgentTranscriptBlocks } from './agent-transcript-blocks';

export const DEBUG_REPRODUCE_PROCEED_MESSAGE =
  "I've reproduced the bug. Please read `.axon/debug-session.ndjson`, analyze the runtime evidence, and continue the debug loop.";

export type DebugReproduceRequest = {
  messageId: string;
  steps: string[];
  source: 'marker';
};

/**
 * Only top-level `:::debug-reproduce` transcript segments count.
 * Mentions inside edit diffs, tool output, or prose must not trigger the banner.
 */
export function parseDebugReproduceSteps(content: string): string[] | null {
  const segments = parseAgentTranscriptBlocks(content);
  for (let index = segments.length - 1; index >= 0; index -= 1) {
    const segment = segments[index];
    if (segment.kind === 'debug-reproduce') {
      return segment.steps;
    }
  }
  return null;
}

export function contentHasDebugReproduceMarker(content: string): boolean {
  return parseDebugReproduceSteps(content) != null;
}

export function extractDebugReproduceRequest(input: {
  messages: Array<{ message_id: string; role: string; content: string }>;
  streaming: boolean;
}): DebugReproduceRequest | null {
  if (input.streaming) {
    return null;
  }
  for (let index = input.messages.length - 1; index >= 0; index -= 1) {
    const message = input.messages[index];
    if (message.role !== 'agent') {
      continue;
    }
    const steps = parseDebugReproduceSteps(message.content);
    if (steps) {
      return { messageId: message.message_id, steps, source: 'marker' };
    }
    // Only inspect the latest agent turn.
    return null;
  }
  return null;
}

export function shouldShowDebugReproduceBanner(input: {
  composerMode: string;
  linkedRunMode?: string | null;
  request: DebugReproduceRequest | null;
  dismissedMessageId: string | null;
}): boolean {
  const debugActive =
    input.composerMode === 'debug' || input.linkedRunMode === 'debug';
  if (!debugActive || !input.request) {
    return false;
  }
  return input.dismissedMessageId !== input.request.messageId;
}
