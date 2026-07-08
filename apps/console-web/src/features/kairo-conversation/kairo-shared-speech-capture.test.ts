import { describe, expect, it, vi, beforeEach } from 'vitest';

import {
  canStartKairoSpeechCapture,
  setKairoSpeechPrivacyBlocked,
  startKairoSpeechCapture,
} from './kairo-shared-speech-capture';
import { kairoConversationPhase, setKairoConversationPhase } from './kairo-conversation-state';

const submitMock = vi.fn(async () => {});

vi.mock('./kairo-conversation-bus', () => ({
  submitKairoConversationTranscript: (...args: unknown[]) => submitMock(...args),
}));

let captureCallbacks: {
  onInterim?: (transcript: string) => void;
  onFinal: (transcript: string) => void;
  onError?: (code: string) => void;
  onEnd?: () => void;
} | null = null;

vi.mock('./speech-capture', () => {
  class MockSpeechCaptureSession {
    start(callbacks: typeof captureCallbacks): boolean {
      captureCallbacks = callbacks;
      return true;
    }

    stop(): void {
      captureCallbacks?.onEnd?.();
    }
  }

  return {
    isSpeechCaptureSupported: () => true,
    SpeechCaptureSession: MockSpeechCaptureSession,
  };
});

describe('kairo-shared-speech-capture busy gating', () => {
  beforeEach(() => {
    submitMock.mockClear();
    captureCallbacks = null;
    setKairoSpeechPrivacyBlocked(() => false);
    setKairoConversationPhase('idle');
  });

  it('submits accepted manual transcripts without blocking on thinking phase', async () => {
    expect(startKairoSpeechCapture('manual')).toBe(true);
    expect(captureCallbacks).not.toBeNull();

    await captureCallbacks!.onFinal('git status');

    expect(submitMock).toHaveBeenCalledWith('git status', { voiceCaptureMode: 'manual' });
    expect(kairoConversationPhase.value).toBe('listening');
  });

  it('blocks capture while thinking', () => {
    setKairoConversationPhase('thinking');
    expect(canStartKairoSpeechCapture()).toBe(false);
    expect(startKairoSpeechCapture('hands_free')).toBe(false);
    expect(kairoConversationPhase.value).toBe('thinking');
  });

  it('blocks capture while speaking', () => {
    setKairoConversationPhase('speaking');
    expect(canStartKairoSpeechCapture()).toBe(false);
    expect(startKairoSpeechCapture('manual')).toBe(false);
  });
});
