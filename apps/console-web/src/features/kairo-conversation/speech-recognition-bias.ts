/**
 * Contextual phrase biasing for browser speech recognition (MDN Web Speech API).
 * Best-effort: APIs are experimental and may be absent in older browsers.
 */

export type SpeechRecognitionBiasPhrase = {
  phrase: string;
  boost: number;
};

/** Domain terms that improve wake-word and workspace recognition. */
export const SPEECH_RECOGNITION_BIAS_PHRASES: readonly SpeechRecognitionBiasPhrase[] = [
  { phrase: 'VAXON', boost: 5 },
  { phrase: 'Vaxon', boost: 4.5 },
  { phrase: 'Axon', boost: 3.5 },
  { phrase: 'Axon Watch', boost: 3.5 },
  { phrase: 'Axon Local', boost: 3.5 },
  { phrase: 'Axon-X', boost: 3.5 },
  { phrase: 'DashPro', boost: 3.5 },
  { phrase: 'briefing', boost: 2.5 },
  { phrase: 'attention', boost: 2.5 },
  { phrase: 'hand it off', boost: 2.5 },
  { phrase: 'hand off', boost: 2 },
  { phrase: 'stop talking', boost: 2 },
  { phrase: 'pause', boost: 2 },
  { phrase: 'resume', boost: 2 },
  { phrase: 'Vax on', boost: 3 },
  { phrase: 'Wax on', boost: 2.5 },
];

type SpeechRecognitionPhraseCtor = new (phrase: string, boost: number) => unknown;

type BiasableSpeechRecognition = {
  processLocally?: boolean;
  phrases?: unknown;
};

export function buildSpeechRecognitionPhraseObjects(
  phraseCtor: SpeechRecognitionPhraseCtor | null | undefined,
  phrases: readonly SpeechRecognitionBiasPhrase[] = SPEECH_RECOGNITION_BIAS_PHRASES,
): unknown[] | null {
  if (!phraseCtor) {
    return null;
  }
  return phrases.map((entry) => new phraseCtor(entry.phrase, entry.boost));
}

export function applySpeechRecognitionBias(recognition: object): void {
  const biasable = recognition as BiasableSpeechRecognition;
  if ('processLocally' in biasable) {
    try {
      biasable.processLocally = true;
    } catch {
      // Browser may reject on-device mode when unavailable.
    }
  }

  if (typeof window === 'undefined' || !('phrases' in biasable)) {
    return;
  }

  const win = window as Window & {
    SpeechRecognitionPhrase?: SpeechRecognitionPhraseCtor;
  };
  const phraseObjects = buildSpeechRecognitionPhraseObjects(win.SpeechRecognitionPhrase);
  if (!phraseObjects?.length) {
    return;
  }

  try {
    biasable.phrases = phraseObjects;
  } catch {
    // ObservableArray assignment may fail on unsupported builds.
  }
}
