import { ref } from 'vue';

import { normalizeVoiceTranscript } from '../../lib/kairo-entity-labels';

/** Matches model lines offering to surface the written briefing panel. */
export const BRIEFING_SURFACE_OFFER_RE =
  /\b(pull\s+(?:it\s+)?to\s+the\s+front|bring\s+(?:it\s+)?(?:up|forward)|open\s+the\s+briefing|shall\s+i\s+(?:pull|show|open))\b/i;

const AFFIRMATIVE_RE = /^(yes|yeah|yep|yup|do it|confirm|go ahead|sure|please)\.?$/i;
const AFFIRMATIVE_PHRASE_RE =
  /\b(pull\s+(?:it\s+)?(?:to\s+the\s+front|up)|bring\s+(?:it\s+)?(?:up|forward)|show\s+(?:me\s+)?(?:the\s+)?briefing|open\s+(?:the\s+)?briefing)\b/i;

/** Keep decision prompts open long enough for an operator to act. */
export const BRIEFING_SURFACE_OFFER_WINDOW_MS = 90_000;

export const briefingSurfaceOfferExpiresAt = ref<number | null>(null);

export function mentionsBriefingSurfaceOffer(text: string): boolean {
  return BRIEFING_SURFACE_OFFER_RE.test(normalizeVoiceTranscript(text));
}

export function isBriefingSurfaceOfferActive(now = Date.now()): boolean {
  const expiresAt = briefingSurfaceOfferExpiresAt.value;
  return expiresAt !== null && now < expiresAt;
}

export function scheduleBriefingSurfaceOffer(now = Date.now()): void {
  briefingSurfaceOfferExpiresAt.value = now + BRIEFING_SURFACE_OFFER_WINDOW_MS;
}

export const BRIEFING_SURFACE_FOLLOWUP_HINT =
  'Say yes or type open briefing to surface the written report.';

export function clearBriefingSurfaceOffer(): void {
  briefingSurfaceOfferExpiresAt.value = null;
}

export function isBriefingSurfaceAffirmation(content: string): boolean {
  const trimmed = normalizeVoiceTranscript(content.trim());
  if (!trimmed) {
    return false;
  }
  return AFFIRMATIVE_RE.test(trimmed) || AFFIRMATIVE_PHRASE_RE.test(trimmed);
}

export function shouldOpenBriefingFromFollowup(content: string, now = Date.now()): boolean {
  return isBriefingSurfaceOfferActive(now) && isBriefingSurfaceAffirmation(content);
}
