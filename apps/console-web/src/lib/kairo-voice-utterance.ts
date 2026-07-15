/** Pub/sub for the text VAXON is currently speaking — Galaxy captions, etc. */

export type KairoVoiceUtteranceListener = (text: string | null) => void;

const utteranceListeners = new Set<KairoVoiceUtteranceListener>();
let currentUtterance: string | null = null;

export function getKairoVoiceUtterance(): string | null {
  return currentUtterance;
}

export function notifyKairoVoiceUtterance(text: string | null): void {
  const next = text?.trim() ? text.trim() : null;
  if (next === currentUtterance) {
    return;
  }
  currentUtterance = next;
  for (const listener of utteranceListeners) {
    listener(currentUtterance);
  }
}

export function subscribeKairoVoiceUtterance(
  listener: KairoVoiceUtteranceListener,
): () => void {
  utteranceListeners.add(listener);
  listener(currentUtterance);
  return () => {
    utteranceListeners.delete(listener);
  };
}

/** Test helper — clear utterance pub/sub state. */
export function resetKairoVoiceUtteranceForTests(): void {
  currentUtterance = null;
  utteranceListeners.clear();
}
