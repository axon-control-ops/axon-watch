/** Display and speech helpers for streaming agent live status lines. */

export const AGENT_LIVE_LINE_DISPLAY_MAX = 96;

/** Third-person operator meta-commentary Cursor often emits in thinking. */
const USER_META_SENTENCE_RE =
  /\b(?:the\s+)?user\s+is\s+asking(?:\s+(?:whether|if|about))?\b[^.!?]*[.!?]?/gi;
const USER_META_ASKED_RE =
  /\b(?:the\s+)?user\s+(?:asked|requested|said|says)\b[^.!?]*[.!?]?/gi;
const USER_META_PREFIX_RE =
  /^(?:\*+)?\s*(?:the\s+)?user\s+(?:is\s+asking(?:\s+(?:whether|if|about))?|asked|requested|said|says)\s*/i;
const LEADING_WHETHER_RE = /^(?:whether|if)\s+/i;

const THINKING_ECHO_MIN = 40;

export function flattenLiveLineText(text: string): string {
  return text.replace(/\s+/g, ' ').trim();
}

function normalizeThinkingEchoCompare(text: string): string {
  return text
    .replace(/^I['']ve\b/i, 've')
    .replace(/^['']ve\b/i, 've')
    .replace(/^I\s+/i, '')
    .replace(/^./, (char) => char.toLowerCase())
    .trim();
}

/**
 * Collapse thinking text that was echoed back-to-back (exact or glued after
 * a sentence end), e.g. "...run.I found ... run." → one copy.
 */
export function collapseBackToBackThinkingEcho(text: string, minLength = THINKING_ECHO_MIN): string {
  const flattened = flattenLiveLineText(text);
  if (flattened.length < minLength * 2) {
    return flattened || text;
  }

  if (flattened.length % 2 === 0) {
    const half = flattened.length / 2;
    if (flattened.slice(0, half) === flattened.slice(half)) {
      return flattened.slice(0, half);
    }
  }

  const tryPair = (left: string, right: string): string | null => {
    if (left.length < minLength || right.length < minLength) {
      return null;
    }
    if (left === right) {
      return left;
    }
    if (normalizeThinkingEchoCompare(left) === normalizeThinkingEchoCompare(right)) {
      return right.length >= left.length ? right : left;
    }
    const shorter = left.length <= right.length ? left : right;
    const longer = left.length <= right.length ? right : left;
    const lengthDelta = Math.abs(left.length - right.length);
    const maxDelta = Math.max(12, Math.floor(shorter.length * 0.15));
    if (
      lengthDelta <= maxDelta &&
      longer.includes(shorter.slice(0, Math.floor(shorter.length * 0.85)))
    ) {
      return longer;
    }
    return null;
  };

  for (let index = minLength; index <= flattened.length - minLength; index += 1) {
    const prev = flattened[index - 1];
    const next = flattened[index];
    if (!prev || !next || !/[.!?]/.test(prev) || !/[A-Z']/.test(next)) {
      continue;
    }
    const collapsed = tryPair(flattened.slice(0, index).trim(), flattened.slice(index).trim());
    if (collapsed) {
      return collapsed;
    }
  }

  // Glued echoes without a sentence boundary — scan near the midpoint.
  const midStart = Math.floor(flattened.length * 0.4);
  const midEnd = Math.ceil(flattened.length * 0.6);
  for (let index = midStart; index <= midEnd; index += 1) {
    const collapsed = tryPair(flattened.slice(0, index).trim(), flattened.slice(index).trim());
    if (collapsed) {
      return collapsed;
    }
  }

  return flattened;
}

/**
 * Strip Cursor thinking that narrates the operator as "the user".
 * Returns operator-facing copy, or empty when nothing usable remains.
 */
export function sanitizeAgentThinkingForOperator(text: string): string {
  let out = collapseBackToBackThinkingEcho(text);
  if (!out) {
    return '';
  }
  out = out.replace(/^\*+|\*+$/g, '').trim();
  out = out.replace(USER_META_SENTENCE_RE, ' ');
  out = out.replace(USER_META_ASKED_RE, ' ');
  out = out.replace(USER_META_PREFIX_RE, '');
  out = out.replace(LEADING_WHETHER_RE, '');
  out = flattenLiveLineText(out).replace(/^[,.\-–—:;]+/, '').trim();
  if (!out || /^(?:the\s+)?user\b/i.test(out) || /^(?:whether|if)\s*$/i.test(out)) {
    return '';
  }
  return out;
}


/** Compact UI copy — never cut mid-word; prefer a sentence boundary. */
export function truncateAgentLiveLineForDisplay(
  text: string,
  maxLength = AGENT_LIVE_LINE_DISPLAY_MAX,
): string {
  const flattened = flattenLiveLineText(text);
  if (flattened.length <= maxLength) {
    return flattened;
  }

  const trimmed = flattened.slice(0, maxLength);
  const sentenceCut = trimmed.lastIndexOf('. ');
  if (sentenceCut >= Math.floor(maxLength * 0.4)) {
    return `${trimmed.slice(0, sentenceCut + 1).trim()}…`;
  }

  const wordCut = trimmed.lastIndexOf(' ');
  if (wordCut >= Math.floor(maxLength * 0.5)) {
    return `${trimmed.slice(0, wordCut).trim()}…`;
  }

  return `${trimmed.trimEnd()}…`;
}

export function isAgentLiveLineTruncated(fullText: string, displayText: string): boolean {
  return flattenLiveLineText(fullText).length > flattenLiveLineText(displayText).replace(/…$/, '').length;
}

/** First one or two complete sentences suitable for live TTS. */
export function firstSpeakableAgentLiveBlock(text: string): string {
  const flattened = sanitizeAgentThinkingForOperator(text);
  if (!flattened) {
    return '';
  }

  const sentences = flattened.match(/[^.!?]+[.!?]+/g) ?? [];
  if (sentences.length === 0) {
    return '';
  }

  let summary = sentences[0]?.trim() ?? '';
  if (summary.length < 120 && sentences.length > 1) {
    summary = `${summary} ${sentences[1].trim()}`;
  }
  return summary;
}
