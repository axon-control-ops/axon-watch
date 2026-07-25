/**
 * Contextual phrase biasing for browser speech recognition (MDN Web Speech API).
 *
 * Phrase lists remain defined for future use / tests, but MUST NOT be assigned on
 * SpeechRecognition in production paths: Chromium on Linux reports
 * `phrases-not-supported` and aborts the entire recognition session.
 */

export type SpeechRecognitionBiasPhrase = {
  phrase: string;
  boost: number;
};

/** Domain terms that improve wake-word and workspace recognition (when supported). */
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

export function buildSpeechRecognitionPhraseObjects(
  phraseCtor: SpeechRecognitionPhraseCtor | null | undefined,
  phrases: readonly SpeechRecognitionBiasPhrase[] = SPEECH_RECOGNITION_BIAS_PHRASES,
): unknown[] | null {
  if (!phraseCtor) {
    return null;
  }
  return phrases.map((entry) => new phraseCtor(entry.phrase, entry.boost));
}

/**
 * Intentionally a no-op for live recognition.
 * Assigning `recognition.phrases` triggers `phrases-not-supported` on Kali/Chromium
 * and prevents any STT results from arriving.
 */
export function applySpeechRecognitionBias(_recognition: object): void {
  // no-op — see file header
}
