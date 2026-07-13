import { describe, expect, it, vi } from 'vitest';

import {
  isSpeechCaptureSupported,
  resolveSpeechRecognitionLang,
  speechRecognitionLangCandidates,
  SpeechCaptureSession,
} from './speech-capture';

describe('speech-capture', () => {
  it('reports unsupported when SpeechRecognition is missing', () => {
    expect(isSpeechCaptureSupported()).toBe(false);
  });

  it('maps regional English like en-ZA to en-US', () => {
    expect(resolveSpeechRecognitionLang('en-ZA')).toBe('en-US');
    expect(resolveSpeechRecognitionLang('en-US')).toBe('en-US');
    expect(resolveSpeechRecognitionLang('en-GB')).toBe('en-GB');
  });

  it('builds language fallback candidates without duplicates', () => {
    expect(speechRecognitionLangCandidates('en-GB')).toEqual(['en-GB', 'en-US', 'en']);
    expect(speechRecognitionLangCandidates('en-ZA')).toEqual(['en-US', 'en-GB', 'en']);
  });

  it('start returns false without browser API', () => {
    const session = new SpeechCaptureSession();
    expect(
      session.start({
        onFinal: vi.fn(),
      }),
    ).toBe(false);
  });
});
