import { onBeforeUnmount } from 'vue';

import {
  isKairoSpeechCaptureSupported,
  kairoCaptureCapturing,
  kairoCaptureError,
  kairoCaptureInterim,
  canStartKairoSpeechCapture,
  setKairoSpeechPrivacyBlocked,
  startKairoSpeechCapture,
  stopKairoSpeechCapture,
} from './kairo-shared-speech-capture';
import type { KairoVoiceCaptureMode } from '../../lib/kairo-voice-gate';

export function useKairoSpeechCapture(options: {
  privacyBlocked: () => boolean;
  captureMode?: KairoVoiceCaptureMode;
}) {
  setKairoSpeechPrivacyBlocked(options.privacyBlocked);

  function canCapture(): boolean {
    return canStartKairoSpeechCapture();
  }

  function startCapture(mode?: KairoVoiceCaptureMode): boolean {
    return startKairoSpeechCapture(mode ?? options.captureMode ?? 'manual');
  }

  function stopCapture(): void {
    stopKairoSpeechCapture();
  }

  onBeforeUnmount(() => {
    stopKairoSpeechCapture();
  });

  return {
    supported: isKairoSpeechCaptureSupported(),
    capturing: kairoCaptureCapturing,
    interimTranscript: kairoCaptureInterim,
    captureError: kairoCaptureError,
    canCapture,
    startCapture,
    stopCapture,
  };
}

export type { KairoVoiceCaptureMode };
