import { onBeforeUnmount } from 'vue';

import {
  isKairoSpeechCaptureSupported,
  kairoCaptureCapturing,
  kairoCaptureError,
  kairoCaptureInterim,
  kairoCaptureLastAccepted,
  kairoCaptureLastGateReason,
  kairoCaptureLastHeard,
  kairoCaptureLastSubmitState,
  kairoCaptureMode,
  canStartKairoSpeechCapture,
  setKairoSpeechPrivacyBlocked,
  startKairoSpeechCapture,
  stopKairoSpeechCapture,
} from './kairo-shared-speech-capture';
import type { KairoVoiceCaptureMode } from '../../lib/kairo-voice-gate';

export function useKairoSpeechCapture(options: {
  privacyBlocked: () => boolean;
  captureMode?: KairoVoiceCaptureMode;
  /** Keep hands-free capture alive when this surface unmounts. */
  stopOnUnmount?: 'always' | 'manual_only' | 'never';
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
    const policy = options.stopOnUnmount ?? 'always';
    if (policy === 'never') {
      return;
    }
    if (policy === 'manual_only' && kairoCaptureMode.value !== 'manual') {
      return;
    }
    stopKairoSpeechCapture();
  });

  return {
    supported: isKairoSpeechCaptureSupported(),
    capturing: kairoCaptureCapturing,
    interimTranscript: kairoCaptureInterim,
    captureError: kairoCaptureError,
    lastHeardTranscript: kairoCaptureLastHeard,
    lastAccepted: kairoCaptureLastAccepted,
    lastGateReason: kairoCaptureLastGateReason,
    lastSubmitState: kairoCaptureLastSubmitState,
    canCapture,
    startCapture,
    stopCapture,
  };
}

export type { KairoVoiceCaptureMode };
