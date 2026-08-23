/**
 * Remember whether the operator already answered the *current* VAXON
 * transmission ask. Only the most recently answered line is tracked (not a
 * lifetime set) — otherwise a repeated identical question in a later turn
 * would be wrongly treated as pre-answered, since Kairo's hint copy reuses
 * similar boilerplate phrasing across unrelated asks.
 */

let lastAnsweredFingerprint: string | null = null;

export function transmissionAskFingerprint(line: string | null | undefined): string {
  return String(line ?? '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .slice(0, 240);
}

export function markTransmissionAskAnswered(line: string | null | undefined): void {
  const key = transmissionAskFingerprint(line);
  lastAnsweredFingerprint = key || null;
}

export function isTransmissionAskAnswered(line: string | null | undefined): boolean {
  const key = transmissionAskFingerprint(line);
  return Boolean(key) && key === lastAnsweredFingerprint;
}

/** Test helper. */
export function resetTransmissionAskAnswersForTests(): void {
  lastAnsweredFingerprint = null;
}
