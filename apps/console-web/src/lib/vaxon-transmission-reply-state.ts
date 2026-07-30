/** Remember which VAXON transmission asks the operator already answered. */

const answeredFingerprints = new Set<string>();

export function transmissionAskFingerprint(line: string | null | undefined): string {
  return String(line ?? '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .slice(0, 240);
}

export function markTransmissionAskAnswered(line: string | null | undefined): void {
  const key = transmissionAskFingerprint(line);
  if (key) {
    answeredFingerprints.add(key);
  }
}

export function isTransmissionAskAnswered(line: string | null | undefined): boolean {
  const key = transmissionAskFingerprint(line);
  return Boolean(key) && answeredFingerprints.has(key);
}

/** Test helper. */
export function resetTransmissionAskAnswersForTests(): void {
  answeredFingerprints.clear();
}
