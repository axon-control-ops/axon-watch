import { describe, expect, it, vi, beforeEach } from 'vitest';

import {
  canStartKairoSpeechCapture,
  kairoCaptureError,
  setKairoSpeechPrivacyBlocked,
  setKairoSpeechSttMode,
  startKairoSpeechCapture,
} from './kairo-shared-speech-capture';
import { kairoConversationPhase, setKairoConversationPhase } from './kairo-conversation-state';

const submitMock = vi.fn<
  (content: string, options?: { voiceCaptureMode?: string }) => Promise<void>
>(async () => {});

vi.mock('./kairo-conversation-bus', () => ({
  submitKairoConversationTranscript: (
    content: string,
    options?: { voiceCaptureMode?: string },
  ) => submitMock(content, options),
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
    setKairoSpeechSttMode(() => 'browser');
    setKairoConversationPhase('idle');
  });

  it('submits accepted manual transcripts without blocking on thinking phase', async () => {
    expect(startKairoSpeechCapture('manual')).toBe(true);
    expect(captureCallbacks).not.toBeNull();

    await captureCallbacks!.onFinal('git status');

    expect(submitMock).toHaveBeenCalledWith('git status', { voiceCaptureMode: 'manual' });
    expect(kairoConversationPhase.value).toBe('listening');
  });

  it('keeps ambient hands-free capture out of the visible conversation phase', () => {
    expect(startKairoSpeechCapture('hands_free')).toBe(true);
    expect(kairoConversationPhase.value).toBe('idle');

    captureCallbacks?.onEnd?.();

    expect(kairoConversationPhase.value).toBe('idle');
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

  it('keeps typing actions available in microphone permission guidance', () => {
    expect(startKairoSpeechCapture('manual')).toBe(true);

    captureCallbacks?.onError?.('not-allowed');

    expect(kairoCaptureError.value).toContain('browser site controls');
    expect(kairoCaptureError.value).toContain('Ask or Dispatch');
  });
});
