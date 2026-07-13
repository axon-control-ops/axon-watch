import { ref } from 'vue';

import { logKairoVoice } from '../../lib/kairo-voice-debug';
import { isKairoVoiceSpeaking } from '../../lib/kairo-voice-playback';
import { normalizeVoiceTranscript } from '../../lib/kairo-entity-labels';
import {
  detectVoiceInterruptPhrase,
  evaluateVoiceTranscript,
  type KairoVoiceCaptureMode,
} from '../../lib/kairo-voice-gate';
import { isSpeechCaptureSupported, SpeechCaptureSession } from './speech-capture';
import { submitKairoConversationTranscript } from './kairo-conversation-bus';
import { kairoConversationPhase, setKairoConversationPhase } from './kairo-conversation-state';

const session = new SpeechCaptureSession();

export const kairoCaptureCapturing = ref(false);
export const kairoCaptureInterim = ref('');
export const kairoCaptureError = ref<string | null>(null);
export const kairoCaptureMode = ref<KairoVoiceCaptureMode>('manual');
export const kairoCaptureLastHeard = ref('');
export const kairoCaptureLastGateReason = ref<string | null>(null);
export const kairoCaptureLastAccepted = ref<boolean | null>(null);
export const kairoCaptureLastSubmitState = ref<'submitted' | 'queued' | 'ignored' | 'dropped' | null>(null);

let privacyBlocked: () => boolean = () => false;
let onVoiceInterrupt: () => void = () => {};
let onCaptureEnd: () => void = () => {};
const captureEndListeners = new Set<() => void>();

let bargeInTriggered = false;

export function registerKairoCaptureEndListener(listener: () => void): () => void {
  captureEndListeners.add(listener);
  return () => {
    captureEndListeners.delete(listener);
  };
}

export function registerKairoVoiceInterruptHandler(handler: () => void): () => void {
  onVoiceInterrupt = handler;
  return () => {
    if (onVoiceInterrupt === handler) {
      onVoiceInterrupt = () => {};
    }
  };
}

export function setKairoSpeechPrivacyBlocked(check: () => boolean): void {
  privacyBlocked = check;
}

function notifyCaptureEnd(): void {
  onCaptureEnd();
  for (const listener of captureEndListeners) {
    listener();
  }
}

export function isKairoSpeechCaptureSupported(): boolean {
  return isSpeechCaptureSupported();
}

function mapCaptureError(code: string): string | null {
  if (code === 'aborted' || code === 'no-speech') {
    return null;
  }
  if (code === 'not-allowed') {
    return 'Microphone permission denied — allow mic access for this site.';
  }
  if (code === 'network') {
    return 'Speech recognition needs network access.';
  }
  if (code === 'start_failed') {
    return 'Could not start speech recognition — try again.';
  }
  return `Speech capture failed (${code}).`;
}

export function canStartKairoSpeechCapture(): boolean {
  return (
    isKairoSpeechCaptureSupported() &&
    !privacyBlocked() &&
    !kairoCaptureCapturing.value &&
    kairoConversationPhase.value !== 'thinking' &&
    kairoConversationPhase.value !== 'speaking'
  );
}

function triggerVoiceInterrupt(source: 'interim' | 'final'): void {
  if (bargeInTriggered) {
    return;
  }
  bargeInTriggered = true;
  logKairoVoice('interrupt', { source, mode: kairoCaptureMode.value });
  onVoiceInterrupt();
  setKairoConversationPhase('idle');
}

function handleInterimTranscript(transcript: string, mode: KairoVoiceCaptureMode): void {
  const normalized = normalizeVoiceTranscript(transcript);
  kairoCaptureInterim.value = normalized;
  if (mode !== 'barge_in') {
    return;
  }
  const trimmed = normalized.trim();
  if (trimmed.length < 3) {
    return;
  }
  if (detectVoiceInterruptPhrase(trimmed)) {
    triggerVoiceInterrupt('interim');
    stopKairoSpeechCapture();
  }
}

async function handleFinalTranscript(transcript: string, mode: KairoVoiceCaptureMode): Promise<void> {
  kairoCaptureInterim.value = '';
  kairoCaptureCapturing.value = false;
  kairoCaptureLastHeard.value = normalizeVoiceTranscript(transcript).trim();

  if (isKairoVoiceSpeaking() || kairoConversationPhase.value === 'speaking') {
    kairoCaptureLastAccepted.value = false;
    kairoCaptureLastGateReason.value = 'voice_output_active';
    kairoCaptureLastSubmitState.value = 'dropped';
    logKairoVoice('final_dropped', {
      transcript,
      mode,
      reason: 'voice_output_active',
    });
    if (kairoConversationPhase.value === 'listening') {
      setKairoConversationPhase('idle');
    }
    notifyCaptureEnd();
    return;
  }

  if (kairoConversationPhase.value === 'thinking') {
    if (detectVoiceInterruptPhrase(normalizeVoiceTranscript(transcript))) {
      triggerVoiceInterrupt('final');
    }
    kairoCaptureLastAccepted.value = false;
    kairoCaptureLastGateReason.value = 'thinking';
    kairoCaptureLastSubmitState.value = 'dropped';
    kairoCaptureCapturing.value = false;
    notifyCaptureEnd();
    return;
  }

  const gate = evaluateVoiceTranscript(transcript, mode);
  logKairoVoice('final', {
    transcript,
    mode,
    accept: gate.accept,
    reason: gate.reason,
    shouldInterrupt: gate.shouldInterrupt,
  });
  kairoCaptureLastAccepted.value = gate.accept;
  kairoCaptureLastGateReason.value = gate.reason;

  if (gate.shouldInterrupt) {
    triggerVoiceInterrupt('final');
  }

  if (!gate.accept || !gate.submitContent) {
    kairoCaptureLastSubmitState.value = 'ignored';
    if (kairoConversationPhase.value === 'listening') {
      setKairoConversationPhase('idle');
    }
    notifyCaptureEnd();
    return;
  }

  kairoCaptureLastSubmitState.value = await submitKairoConversationTranscript(gate.submitContent, {
    voiceCaptureMode: mode,
  });
  notifyCaptureEnd();
}

export function startKairoSpeechCapture(mode: KairoVoiceCaptureMode = 'manual'): boolean {
  if (kairoConversationPhase.value === 'thinking' || kairoConversationPhase.value === 'speaking') {
    return false;
  }
  if (!canStartKairoSpeechCapture()) {
    return false;
  }

  kairoCaptureMode.value = mode;
  bargeInTriggered = false;
  kairoCaptureError.value = null;
  kairoCaptureInterim.value = '';
  setKairoConversationPhase('listening');

  const started = session.start({
    onInterim: (transcript) => {
      handleInterimTranscript(transcript, mode);
    },
    onFinal: (transcript) => {
      void handleFinalTranscript(transcript, mode);
    },
    onError: (code) => {
      kairoCaptureCapturing.value = false;
      kairoCaptureInterim.value = '';
      kairoCaptureError.value = mapCaptureError(code);
      setKairoConversationPhase('idle');
      notifyCaptureEnd();
    },
    onEnd: () => {
      const pendingTranscript = kairoCaptureInterim.value.trim();
      kairoCaptureCapturing.value = false;
      kairoCaptureInterim.value = '';
      if (pendingTranscript && !bargeInTriggered) {
        void handleFinalTranscript(pendingTranscript, kairoCaptureMode.value);
        return;
      }
      if (kairoConversationPhase.value === 'listening') {
        setKairoConversationPhase('idle');
      }
      notifyCaptureEnd();
    },
  });

  kairoCaptureCapturing.value = started;
  if (!started) {
    setKairoConversationPhase('idle');
  } else {
    logKairoVoice('capture_start', { mode });
  }
  return started;
}

export function stopKairoSpeechCapture(): void {
  session.stop();
}
