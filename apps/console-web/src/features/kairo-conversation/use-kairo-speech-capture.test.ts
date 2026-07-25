import { describe, expect, it, vi } from 'vitest';

import { useKairoSpeechCapture } from './use-kairo-speech-capture';

vi.mock('./speech-capture', () => {
  class MockSpeechCaptureSession {
    start(): boolean {
      return false;
    }

    stop(): void {}
  }

  return {
    isSpeechCaptureSupported: () => true,
    SpeechCaptureSession: MockSpeechCaptureSession,
  };
});

describe('useKairoSpeechCapture', () => {
  it('does not stay capturing when session start fails', () => {
    const hook = useKairoSpeechCapture({
      privacyBlocked: () => false,
    });

    expect(hook.startCapture()).toBe(false);
    expect(hook.capturing.value).toBe(false);
  });
});
