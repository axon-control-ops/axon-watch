/** Display and speech helpers for streaming agent live status lines. */

export const AGENT_LIVE_LINE_DISPLAY_MAX = 96;

export function flattenLiveLineText(text: string): string {
  return text.replace(/\s+/g, ' ').trim();
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

/** First complete sentence block suitable for TTS — skip partial fragments. */
export function firstSpeakableAgentLiveBlock(text: string): string {
  const flattened = flattenLiveLineText(text);
  if (!flattened) {
    return '';
  }

  const sentences = flattened.match(/[^.!?]+[.!?]+/g) ?? [];
  if (sentences.length === 0) {
    return '';
  }

  return sentences[0]?.trim() ?? '';
}
