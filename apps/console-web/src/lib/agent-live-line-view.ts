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
/** Near-duplicate paragraphs (typos / glued words) still count as an echo. */
const THINKING_ECHO_SIMILARITY = 0.82;

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

/** Strip markup/noise and split glued words so near-echoes compare cleanly. */
function normalizeThinkingEchoTokens(text: string): string {
  return text
    .replace(/[*_`~]/g, '')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/([A-Za-z])(\d)/g, '$1 $2')
    .toLowerCase()
    .replace(/[^\w\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function thinkingEchoTokenSimilarity(left: string, right: string): number {
  const aTokens = normalizeThinkingEchoTokens(left).split(' ').filter(Boolean);
  const bTokens = normalizeThinkingEchoTokens(right).split(' ').filter(Boolean);
  if (aTokens.length === 0 || bTokens.length === 0) {
    return 0;
  }
  const aSet = new Set(aTokens);
  const bSet = new Set(bTokens);
  let intersection = 0;
  for (const token of aSet) {
    if (bSet.has(token)) {
      intersection += 1;
    }
  }
  const union = aSet.size + bSet.size - intersection;
  return union === 0 ? 0 : intersection / union;
}

function preferThinkingEchoCopy(left: string, right: string): string {
  // Prefer the copy that reads more naturally (spaces, leading "I ").
  const score = (value: string): number => {
    let points = value.length;
    if (/^I\s/i.test(value)) {
      points += 8;
    }
    if (!/\bthe[A-Z]/.test(value) && !/\buse[A-Z]/.test(value)) {
      points += 4;
    }
    if (!/\*/.test(value)) {
      points += 2;
    }
    return points;
  };
  return score(right) >= score(left) ? right : left;
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
      return preferThinkingEchoCopy(left, right);
    }
    const shorter = left.length <= right.length ? left : right;
    const longer = left.length <= right.length ? right : left;
    const lengthDelta = Math.abs(left.length - right.length);
    const maxDelta = Math.max(24, Math.floor(shorter.length * 0.2));
    if (lengthDelta <= maxDelta) {
      const prefix = shorter.slice(0, Math.floor(shorter.length * 0.85));
      if (longer.includes(prefix)) {
        return preferThinkingEchoCopy(left, right);
      }
      if (thinkingEchoTokenSimilarity(left, right) >= THINKING_ECHO_SIMILARITY) {
        return preferThinkingEchoCopy(left, right);
      }
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
/** Strip leaked stream fence markers (e.g. trailing `:::` glued onto a sentence). */
export function stripAgentStreamFenceMarkers(text: string): string {
  return flattenLiveLineText(text)
    .replace(/^:::(?:thinking|tool|edit|terminal|research|debug-reproduce)?\b\s*/i, '')
    .replace(/(?:^|\s):::\s*$/g, '')
    .replace(/\s+:::(?=\s|$)/g, ' ')
    .trim();
}

/** Operator-facing fallback when thinking has no usable body. */
export const THINKING_SPEECH_FALLBACK = 'On it…';

/**
 * Prefer short "On it…" chrome over bare "Thinking…" / "I am thinking…" labels
 * (milestones, model lead-ins, and OCR-prone transcript chips).
 */
export function normalizeThinkingSpeechLead(text: string): string {
  const flattened = flattenLiveLineText(text);
  if (!flattened) {
    return '';
  }
  if (/^(?:i\s+am\s+)?thinking(?:[.…]{1,3}|\.\.\.)?$/i.test(flattened)) {
    return THINKING_SPEECH_FALLBACK;
  }
  if (/^i\s+am\s+thinking\b/i.test(flattened)) {
    const rest = flattened.replace(/^i\s+am\s+thinking(?:[.…]{1,3}|\.\.\.)?\s*/i, '').trim();
    return rest ? `On it — ${rest}` : THINKING_SPEECH_FALLBACK;
  }
  if (/^thinking\b/i.test(flattened)) {
    const rest = flattened.replace(/^thinking(?:[.…]{1,3}|\.\.\.)?\s*/i, '').trim();
    return rest ? `On it — ${rest}` : THINKING_SPEECH_FALLBACK;
  }
  return flattened;
}

export function sanitizeAgentThinkingForOperator(text: string): string {
  let out = collapseBackToBackThinkingEcho(text);
  if (!out) {
    return '';
  }
  out = stripAgentStreamFenceMarkers(out);
  out = out.replace(/^\*+|\*+$/g, '').trim();
  out = out.replace(USER_META_SENTENCE_RE, ' ');
  out = out.replace(USER_META_ASKED_RE, ' ');
  out = out.replace(USER_META_PREFIX_RE, '');
  out = out.replace(LEADING_WHETHER_RE, '');
  out = flattenLiveLineText(out).replace(/^[,.\-–—:;]+/, '').trim();
  out = stripAgentStreamFenceMarkers(out);
  out = normalizeThinkingSpeechLead(out);
  if (!out || /^(?:the\s+)?user\b/i.test(out) || /^(?:whether|if)\s*$/i.test(out)) {
    return '';
  }
  return out;
}

/** Wait/poll status chatter — speak once per turn, not on every Await cycle. */
const WAIT_PROGRESS_RE =
  /\b(?:still\s+(?:running|progressing|waiting|building|bundling|active)|build\s+is\s+still|cache\s+is\s+active|waiting\s+for|polling|no\s+new\s+output|checking\s+the\s+terminal)\b/i;

export function isWaitProgressThinking(text: string): boolean {
  return WAIT_PROGRESS_RE.test(stripAgentStreamFenceMarkers(text));
}

/** Token Jaccard similarity for near-duplicate spoken thinking lines. */
export function thinkingSpeechSimilarity(left: string, right: string): number {
  return thinkingEchoTokenSimilarity(left, right);
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
