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

export function flattenLiveLineText(text: string): string {
  return text.replace(/\s+/g, ' ').trim();
}

/**
 * Strip Cursor thinking that narrates the operator as "the user".
 * Returns operator-facing copy, or empty when nothing usable remains.
 */
export function sanitizeAgentThinkingForOperator(text: string): string {
  let out = flattenLiveLineText(text);
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

/** First complete sentence block suitable for TTS — skip partial / meta fragments. */
export function firstSpeakableAgentLiveBlock(text: string): string {
  const flattened = sanitizeAgentThinkingForOperator(text);
  if (!flattened) {
    return '';
  }

  const sentences = flattened.match(/[^.!?]+[.!?]+/g) ?? [];
  if (sentences.length === 0) {
    return '';
  }

  return sentences[0]?.trim() ?? '';
}
