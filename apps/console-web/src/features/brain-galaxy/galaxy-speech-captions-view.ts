/** Pure helpers for Galaxy floating speech captions. */

/** Slow drift presentation — advance timing comes from narration chunk starts. */
export const GALAXY_CAPTION_FLOAT_MS = 10_000;
/** One sentence on stage at a time. */
export const GALAXY_CAPTION_MAX_VISIBLE = 1;

export type GalaxySpeechCaption = {
  id: string;
  text: string;
  bornAt: number;
};

export type GalaxyNarrationSentenceStep = {
  phrase: string;
  /** Delay from the narration chunk start before this sentence should appear. */
  delayMs: number;
};

/** Split spoken prose into one HUD line per sentence (no mid-sentence chops). */
export function splitGalaxySpeechPhrases(text: string): string[] {
  const normalized = text.replace(/\s+/g, ' ').trim();
  if (!normalized) {
    return [];
  }

  const sentences = normalized.match(/[^.!?]+[.!?]+|[^.!?]+$/g) ?? [normalized];
  return sentences.map((sentence) => sentence.trim()).filter(Boolean);
}

function wordCount(phrase: string): number {
  return phrase.trim().split(/\s+/).filter(Boolean).length;
}

/**
 * Intra-chunk sentence steps gated by narration chunk start.
 * Word-share delays only kick in after the chunk begins playing.
 */
export function buildNarrationSentenceSteps(
  chunkText: string,
  msPerWord = 420,
): GalaxyNarrationSentenceStep[] {
  const sentences = splitGalaxySpeechPhrases(chunkText);
  if (sentences.length === 0) {
    return [];
  }
  if (sentences.length === 1) {
    return [{ phrase: sentences[0]!, delayMs: 0 }];
  }

  const totalWords = Math.max(
    1,
    sentences.reduce((sum, sentence) => sum + wordCount(sentence), 0),
  );
  const totalMs = Math.min(18_000, Math.max(2_400, totalWords * msPerWord));
  let elapsed = 0;
  return sentences.map((phrase) => {
    const step = { phrase, delayMs: Math.round(elapsed) };
    elapsed += (wordCount(phrase) / totalWords) * totalMs;
    return step;
  });
}

/** @deprecated Prefer buildNarrationSentenceSteps — wall-clock schedules drift from TTS. */
export function estimateGalaxyCaptionDurationMs(phrase: string): number {
  const words = wordCount(phrase);
  const fromWords = Math.max(1, words) * 500;
  const fromChars = Math.max(1, phrase.trim().length) * 55;
  const estimated = Math.round((fromWords + fromChars) / 2);
  return Math.min(
    16_000,
    Math.max(Math.round(GALAXY_CAPTION_FLOAT_MS * 0.9), estimated),
  );
}

/** @deprecated Prefer narration-chunk gated steps. */
export function buildGalaxySpeechCaptionSchedule(
  text: string,
  startedAt = Date.now(),
): Array<{ phrase: string; startAt: number; durationMs: number }> {
  const phrases = splitGalaxySpeechPhrases(text);
  let cursor = startedAt;
  return phrases.map((phrase) => {
    const durationMs = estimateGalaxyCaptionDurationMs(phrase);
    const entry = { phrase, startAt: cursor, durationMs };
    cursor += durationMs;
    return entry;
  });
}
