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
  setKairoSpeechSttMode,
  startKairoSpeechCapture,
  stopKairoSpeechCapture,
} from './kairo-shared-speech-capture';
import type { KairoVoiceCaptureMode } from '../../lib/kairo-voice-gate';

export function useKairoSpeechCapture(options: {
  privacyBlocked: () => boolean;
  sttMode?: () => string;
  captureMode?: KairoVoiceCaptureMode;
  /** Keep hands-free capture alive when this surface unmounts. */
  stopOnUnmount?: 'always' | 'manual_only' | 'never';
}) {
  setKairoSpeechPrivacyBlocked(options.privacyBlocked);
  if (options.sttMode) {
    setKairoSpeechSttMode(options.sttMode);
  }

  function canCapture(): boolean {
    return canStartKairoSpeechCapture();
  }

  function startCapture(
    mode?: KairoVoiceCaptureMode,
    startOptions?: { takeover?: boolean },
  ): boolean {
    return startKairoSpeechCapture(mode ?? options.captureMode ?? 'manual', startOptions);
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
    captureMode: kairoCaptureMode,
    canCapture,
    startCapture,
    stopCapture,
  };
}

export type { KairoVoiceCaptureMode };
