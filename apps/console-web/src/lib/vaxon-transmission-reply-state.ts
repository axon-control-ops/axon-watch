/** Remember which VAXON transmission asks the operator already answered. */

import { ref } from 'vue';

const answeredFingerprints = new Set<string>();
export const pendingTransmissionAsk = ref<string | null>(null);

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
    if (transmissionAskFingerprint(pendingTransmissionAsk.value) === key) {
      pendingTransmissionAsk.value = null;
    }
  }
}

export function isTransmissionAskAnswered(line: string | null | undefined): boolean {
  const key = transmissionAskFingerprint(line);
  return Boolean(key) && answeredFingerprints.has(key);
}

/** Keep an unanswered decision visible even when a later status line arrives. */
export function retainTransmissionAsk(line: string | null | undefined): void {
  const cleaned = String(line ?? '').trim();
  if (!cleaned || isTransmissionAskAnswered(cleaned)) {
    return;
  }
  pendingTransmissionAsk.value = cleaned;
}

/** Test helper. */
export function resetTransmissionAskAnswersForTests(): void {
  answeredFingerprints.clear();
  pendingTransmissionAsk.value = null;
}
