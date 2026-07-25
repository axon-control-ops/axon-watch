import { describe, expect, it, vi } from 'vitest';

import {
  SPEECH_RECOGNITION_BIAS_PHRASES,
  applySpeechRecognitionBias,
  buildSpeechRecognitionPhraseObjects,
} from './speech-recognition-bias';

describe('speech-recognition-bias', () => {
  it('includes VAXON and workspace phrases', () => {
    const phrases = SPEECH_RECOGNITION_BIAS_PHRASES.map((entry) => entry.phrase);
    expect(phrases).toContain('VAXON');
    expect(phrases).toContain('DashPro');
    expect(phrases).toContain('Axon Watch');
  });

  it('builds phrase objects when SpeechRecognitionPhrase is available', () => {
    class MockPhrase {
      phrase: string;
      boost: number;
      constructor(phrase: string, boost: number) {
        this.phrase = phrase;
        this.boost = boost;
      }
    }
    const objects = buildSpeechRecognitionPhraseObjects(MockPhrase, [
      { phrase: 'VAXON', boost: 5 },
    ]);
    expect(objects).toHaveLength(1);
    expect(objects?.[0]).toEqual({ phrase: 'VAXON', boost: 5 });
  });

  it('returns null when SpeechRecognitionPhrase is missing', () => {
    expect(buildSpeechRecognitionPhraseObjects(null)).toBeNull();
  });

  it('does not assign phrases on live recognition (Kali/Chromium crash path)', () => {
    const recognition = {
      processLocally: false,
      phrases: undefined as unknown,
    };
    class MockPhrase {
      constructor(
        public phrase: string,
        public boost: number,
      ) {}
    }
    vi.stubGlobal('window', { SpeechRecognitionPhrase: MockPhrase });

    applySpeechRecognitionBias(recognition);

    expect(recognition.processLocally).toBe(false);
    expect(recognition.phrases).toBeUndefined();

    vi.unstubAllGlobals();
  });
});
