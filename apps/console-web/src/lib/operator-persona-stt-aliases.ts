/** Canonical wake-word label used after STT normalization. */
const PERSONA_CANONICAL_NAME = 'VAXON';

/**
 * Common Web Speech API mishears for the VAXON wake word.
 * Order matters: longer / more specific patterns first.
 */
export const PERSONA_STT_MISHEAR_REPLACEMENTS: ReadonlyArray<[RegExp, string]> = [
  // Spelled or dotted: "V A X O N", "V-A-X-O-N"
  [/\bv[\s.\-_]*a[\s.\-_]*x[\s.\-_]*o[\s.\-_]*n\b/gi, PERSONA_CANONICAL_NAME],
  // TTS phonetic spelling must never leak into on-screen transcripts.
  [/\bvekson\b/gi, PERSONA_CANONICAL_NAME],

  // Legacy operator persona names
  [/\bkairos\b/gi, PERSONA_CANONICAL_NAME],
  [/\bkairo\b/gi, PERSONA_CANONICAL_NAME],
  [/\bcairo\b/gi, PERSONA_CANONICAL_NAME],
  [/\bkyro\b/gi, PERSONA_CANONICAL_NAME],

  // Axon + persona compound ("axon vaxon", "axon vixen")
  [
    /\baxon[\s-]+v(?:ax|ix|ex|ick|ik|ack|ox|ux|ics|ic)[a-z]*(?:on|en|in|an|om|un)?\b/gi,
    PERSONA_CANONICAL_NAME,
  ],

  // Two-word STT splits
  [/\bvax[\s-]+on\b/gi, PERSONA_CANONICAL_NAME],
  [/\bwax[\s-]+on\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvex[\s-]+on\b/gi, PERSONA_CANONICAL_NAME],
  [/\bfix[\s-]+on\b/gi, PERSONA_CANONICAL_NAME],
  [/\bbacks?[\s-]+on\b/gi, PERSONA_CANONICAL_NAME],
  [/\bback[\s-]+son\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvack[\s-]+s?[\s-]*on\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvic(?:k|s)?[\s-]+s?[\s-]*on\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvi(?:ck|x|k)?[\s-]+s?[\s-]*on\b/gi, PERSONA_CANONICAL_NAME],

  // Explicit mishears (operator-reported + common phonetic drift)
  [/\bvicksen\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvicksin\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvickson\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvickzon\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvikson\b/gi, PERSONA_CANONICAL_NAME],
  [/\bviksen\b/gi, PERSONA_CANONICAL_NAME],
  [/\bviksin\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvicson\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvicsen\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvicen\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvixson\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvixen\b/gi, PERSONA_CANONICAL_NAME],
  [/\bwixen\b/gi, PERSONA_CANONICAL_NAME],
  [/\bwicksen\b/gi, PERSONA_CANONICAL_NAME],
  [/\bwikson\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvic+[kt]?sen\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvi[ckx]{1,2}s?[oei]n\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvaxen\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvaxin\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvexeon\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvexon\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvexen\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvexin\b/gi, PERSONA_CANONICAL_NAME],
  [/\bwexon\b/gi, PERSONA_CANONICAL_NAME],
  [/\bwaxon\b/gi, PERSONA_CANONICAL_NAME],
  [/\bnaxon\b/gi, PERSONA_CANONICAL_NAME],
  [/\bbaxon\b/gi, PERSONA_CANONICAL_NAME],
  [/\bmaxon\b/gi, PERSONA_CANONICAL_NAME],
  [/\bfaxon\b/gi, PERSONA_CANONICAL_NAME],
  [/\bfixon\b/gi, PERSONA_CANONICAL_NAME],
  [/\bphaxon\b/gi, PERSONA_CANONICAL_NAME],
  [/\bpaxon\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvaxom\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvexom\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvixon\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvyxon\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvacon\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvackon\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvagon\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvakson\b/gi, PERSONA_CANONICAL_NAME],
  [/\bpackson\b/gi, PERSONA_CANONICAL_NAME],
  // Operator-reported mishears from Kali/Chromium STT
  [/\bvaccine\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvaccines\b/gi, PERSONA_CANONICAL_NAME],
  [/\bvaccinate\b/gi, PERSONA_CANONICAL_NAME],
  [/\bericsson\b/gi, PERSONA_CANONICAL_NAME],
  [/\beric[\s-]+son\b/gi, PERSONA_CANONICAL_NAME],
  [/\berickson\b/gi, PERSONA_CANONICAL_NAME],
  [/\brex[\s-]+on\b/gi, PERSONA_CANONICAL_NAME],
  [/\brexon\b/gi, PERSONA_CANONICAL_NAME],
];

/** Conservative phonetic fallback for v*…on wake fragments not caught above. */
export const PERSONA_STT_PHONETIC_VAXON_RE =
  /\b[vwbfmpn][aeiouy]?[ -]?(?:ax|ex|ix|ick|iks|ik|ack|acs|ox|ux|ics|ic|ec)(?:[a-z]{0,2})?(?:on|en|in|an|om|un)\b/gi;

const CANONICAL_WAKE_RE = new RegExp(
  `\\b(${PERSONA_CANONICAL_NAME}|naxon|kairo|cairo|kyro|kairos|x|ex)\\b`,
  'i',
);

export function normalizePersonaSttAliases(text: string): string {
  let result = text;
  for (const [pattern, replacement] of PERSONA_STT_MISHEAR_REPLACEMENTS) {
    result = result.replace(pattern, replacement);
  }
  result = result.replace(PERSONA_STT_PHONETIC_VAXON_RE, PERSONA_CANONICAL_NAME);
  return result;
}

/** Score how likely a raw transcript contains the VAXON wake word (for STT alternative pick). */
export function personaWakeMatchScore(text: string): number {
  const trimmed = text.trim();
  if (!trimmed) {
    return 0;
  }
  const normalized = normalizePersonaSttAliases(trimmed);
  if (new RegExp(`\\b${PERSONA_CANONICAL_NAME}\\b`, 'i').test(normalized)) {
    return 100;
  }
  if (CANONICAL_WAKE_RE.test(normalized)) {
    return 80;
  }
  if (PERSONA_STT_PHONETIC_VAXON_RE.test(trimmed)) {
    return 60;
  }
  for (const [pattern] of PERSONA_STT_MISHEAR_REPLACEMENTS) {
    pattern.lastIndex = 0;
    if (pattern.test(trimmed)) {
      return 50;
    }
  }
  return 0;
}

export function pickBestSpeechTranscript(alternatives: readonly string[]): string {
  const candidates = alternatives.map((item) => item.trim()).filter(Boolean);
  if (candidates.length === 0) {
    return '';
  }
  let best = candidates[0]!;
  let bestScore = personaWakeMatchScore(best);
  for (let index = 1; index < candidates.length; index += 1) {
    const candidate = candidates[index]!;
    const score = personaWakeMatchScore(candidate);
    if (score > bestScore) {
      best = candidate;
      bestScore = score;
    }
  }
  return best;
}

export function hasPersonaWakeHint(text: string): boolean {
  return personaWakeMatchScore(text) >= 50;
}
