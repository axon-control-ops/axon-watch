/** Cursor-style Debug Mode: parse reproduce pauses and build the proceed follow-up. */

import { parseAgentTranscriptBlocks } from './agent-transcript-blocks';

export const DEBUG_REPRODUCE_PROCEED_MESSAGE =
  "I've reproduced the bug. Please read `.axon/debug-session.ndjson`, analyze the runtime evidence, and continue the debug loop.";

/** Cursor-like banner: keep reproduce actions short and human-facing. */
export const DEBUG_REPRODUCE_STEP_CAP = 4;

export type DebugReproduceRequest = {
  messageId: string;
  steps: string[];
  source: 'marker';
};

const HYPOTHESIS_LABEL_RE = /^(?:\+?\s*)?H\d+\s*(?:[—\-:]|\bhypothesis\b)/i;
const INSTRUMENTATION_LINE_RE =
  /\b(?:hypothesisId|NDJSON|debug-session\.ndjson|instrument(?:ation|ing)?|log statements?)\b/i;

function stripMarkdownDecorations(text: string): string {
  return text
    .replace(/\*\*/g, '')
    .replace(/__/g, '')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/(^|[\s(])\*([^*\n]+)\*([\s).,;:!?]|$)/g, '$1$2$3')
    .replace(/^#{1,6}\s+/, '')
    .replace(/^\+\s+/, '')
    .trim();
}

function isHypothesisOrInstrumentationLine(text: string): boolean {
  return HYPOTHESIS_LABEL_RE.test(text) || INSTRUMENTATION_LINE_RE.test(text);
}

/**
 * Cursor Debug Mode shows a short list of user actions to reproduce — not the
 * full hypothesis/instrumentation dump. Sanitize model output so the banner stays usable.
 */
export function sanitizeDebugReproduceSteps(steps: string[]): string[] {
  const cleaned: string[] = [];
  const seen = new Set<string>();

  for (const raw of steps) {
    const step = stripMarkdownDecorations(
      raw.replace(/^\s*(?:\d+[.)]|-\s+|\*\s+)\s*/, '').trim(),
    );
    if (!step || isHypothesisOrInstrumentationLine(step)) {
      continue;
    }
    const key = step.toLowerCase();
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    cleaned.push(step);
    if (cleaned.length >= DEBUG_REPRODUCE_STEP_CAP) {
      break;
    }
  }

  return cleaned.length > 0
    ? cleaned
    : ['Reproduce the bug using the steps above, then proceed.'];
}

/**
 * Only top-level `:::debug-reproduce` transcript segments count.
 * Mentions inside edit diffs, tool output, or prose must not trigger the banner.
 */
export function parseDebugReproduceSteps(content: string): string[] | null {
  const segments = parseAgentTranscriptBlocks(content);
  for (let index = segments.length - 1; index >= 0; index -= 1) {
    const segment = segments[index];
    if (segment.kind === 'debug-reproduce') {
      return sanitizeDebugReproduceSteps(segment.steps);
    }
  }
  return null;
}

export function contentHasDebugReproduceMarker(content: string): boolean {
  const segments = parseAgentTranscriptBlocks(content);
  return segments.some((segment) => segment.kind === 'debug-reproduce');
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
