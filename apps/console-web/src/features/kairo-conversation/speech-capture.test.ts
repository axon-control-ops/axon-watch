import { describe, expect, it, vi } from 'vitest';

import { isSpeechCaptureSupported, SpeechCaptureSession } from './speech-capture';

describe('speech-capture', () => {
  it('reports unsupported when SpeechRecognition is missing', () => {
    expect(isSpeechCaptureSupported()).toBe(false);
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
